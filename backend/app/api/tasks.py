import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import ActivityEvent, Membership, Property, PropertyTask, User
from app.schemas.tasks import MemberOut, TaskCreate, TaskOut, TaskUpdate
from app.services.ics import task_ics
from app.services.notifications import create_notification_event
from app.services.outbox import record_audit
from app.services.properties import check_row_version


router = APIRouter(tags=["tasks"])


def _local_due_at(value: datetime | None, timezone: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value
    try:
        return value.replace(tzinfo=ZoneInfo(timezone))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Timezone must be a valid IANA timezone.") from exc


async def _task(db: AsyncSession, journey_id: uuid.UUID, workspace_id: uuid.UUID, task_id: uuid.UUID) -> PropertyTask:
    task = (
        await db.execute(
            select(PropertyTask).where(
                PropertyTask.id == task_id,
                PropertyTask.journey_id == journey_id,
                PropertyTask.workspace_id == workspace_id,
                PropertyTask.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _task_out(db: AsyncSession, task: PropertyTask) -> TaskOut:
    property_address = None
    if task.property_id:
        prop = (await db.execute(select(Property).where(Property.id == task.property_id))).scalar_one_or_none()
        property_address = f"{prop.address_line}, {prop.suburb} {prop.state}" if prop else None
    assignee_name = None
    if task.assignee_user_id:
        assignee_name = (await db.execute(select(User.display_name).where(User.id == task.assignee_user_id))).scalar_one_or_none()
    return TaskOut(
        id=task.id, journey_id=task.journey_id, property_id=task.property_id, property_address=property_address,
        title=task.title, notes=task.notes, assignee_user_id=task.assignee_user_id, assignee_name=assignee_name,
        priority=task.priority, due_at=task.due_at, timezone=task.timezone,
        reminder_offset_minutes=task.reminder_offset_minutes, status=task.status, done=task.done,
        done_at=task.done_at, row_version=task.row_version, created_at=task.created_at, updated_at=task.updated_at,
    )


async def _valid_property(db: AsyncSession, journey_id: uuid.UUID, workspace_id: uuid.UUID, property_id: uuid.UUID | None) -> None:
    if property_id is None:
        return
    prop = (
        await db.execute(
            select(Property.id).where(Property.id == property_id, Property.journey_id == journey_id, Property.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")


async def _valid_assignee(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    if user_id is None:
        return
    member = (
        await db.execute(select(Membership.id).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id))
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Assignee not found")


@router.get("/workspaces/me/members", response_model=list[MemberOut])
async def workspace_members(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> list[MemberOut]:
    rows = (
        await db.execute(
            select(User, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.workspace_id == auth.workspace.id)
            .order_by(Membership.created_at)
        )
    ).all()
    return [MemberOut(id=user.id, display_name=user.display_name, email=user.email, role=role) for user, role in rows]


@router.get("/journeys/{journey_id}/tasks", response_model=list[TaskOut])
async def list_tasks(journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> list[TaskOut]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    rows = (
        await db.execute(
            select(PropertyTask).where(
                PropertyTask.journey_id == journey.id, PropertyTask.workspace_id == journey.workspace_id,
                PropertyTask.deleted_at.is_(None),
            ).order_by(PropertyTask.done, PropertyTask.due_at.is_(None), PropertyTask.due_at, PropertyTask.created_at.desc())
        )
    ).scalars().all()
    return [await _task_out(db, task) for task in rows]


@router.post("/journeys/{journey_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    journey_id: uuid.UUID, body: TaskCreate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> TaskOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    await _valid_property(db, journey.id, journey.workspace_id, body.property_id)
    assignee_id = body.assignee_user_id or auth.user.id
    await _valid_assignee(db, journey.workspace_id, assignee_id)
    task = PropertyTask(
        workspace_id=journey.workspace_id, journey_id=journey.id, property_id=body.property_id,
        title=body.title.strip(), notes=body.notes.strip() if body.notes else None, assignee_user_id=assignee_id,
        priority=body.priority, due_at=_local_due_at(body.due_at, body.timezone), timezone=body.timezone, reminder_offset_minutes=body.reminder_offset_minutes,
        status="open", done=False, created_by=auth.user.id,
    )
    db.add(task)
    await db.flush()
    db.add(ActivityEvent(workspace_id=journey.workspace_id, journey_id=journey.id, property_id=task.property_id, kind="task_created", summary=f"Created task: {task.title}", detail={"task_id": str(task.id)}, actor_user_id=auth.user.id))
    await record_audit(db, action="task_created", actor_user_id=auth.user.id, workspace_id=journey.workspace_id, subject=str(task.id))
    await create_notification_event(
        db, workspace_id=journey.workspace_id, category="task_assigned", fingerprint=f"task:{task.id}:assigned:{assignee_id}",
        title=f"Task assigned: {task.title}", message="A task was assigned to you.", safe_deep_link=f"/app/tasks?task={task.id}",
        priority="normal", property_id=task.property_id, task_id=task.id, recipient_ids={assignee_id}, evidence_ref={"task_id": str(task.id)},
    )
    await db.commit()
    await db.refresh(task)
    return await _task_out(db, task)


@router.get("/journeys/{journey_id}/tasks/{task_id}", response_model=TaskOut)
async def get_task(journey_id: uuid.UUID, task_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> TaskOut:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    return await _task_out(db, await _task(db, journey.id, journey.workspace_id, task_id))


@router.patch("/journeys/{journey_id}/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    journey_id: uuid.UUID, task_id: uuid.UUID, body: TaskUpdate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> TaskOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    task = await _task(db, journey.id, journey.workspace_id, task_id)
    check_row_version(task.row_version, body.expected_row_version, "task")
    if "property_id" in body.model_fields_set:
        await _valid_property(db, journey.id, journey.workspace_id, body.property_id)
        task.property_id = body.property_id
    if "assignee_user_id" in body.model_fields_set and body.assignee_user_id is not None:
        await _valid_assignee(db, journey.workspace_id, body.assignee_user_id)
        task.assignee_user_id = body.assignee_user_id
    for field in ("title", "notes", "priority", "due_at", "timezone", "reminder_offset_minutes"):
        if field in body.model_fields_set:
            value = getattr(body, field)
            setattr(task, field, _local_due_at(value, body.timezone or task.timezone) if field == "due_at" else value.strip() if isinstance(value, str) else value)
    if body.status is not None:
        task.status = body.status
        task.done = body.status == "completed"
        task.done_at = now_utc() if task.done else None
    task.row_version += 1
    db.add(ActivityEvent(workspace_id=journey.workspace_id, journey_id=journey.id, property_id=task.property_id, kind="task_completed" if task.done else "task_updated", summary=f"{'Completed' if task.done else 'Updated'} task: {task.title}", detail={"task_id": str(task.id)}, actor_user_id=auth.user.id))
    await record_audit(db, action="task_updated", actor_user_id=auth.user.id, workspace_id=journey.workspace_id, subject=str(task.id))
    await db.commit()
    await db.refresh(task)
    return await _task_out(db, task)


@router.delete("/journeys/{journey_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(journey_id: uuid.UUID, task_id: uuid.UUID, expected_row_version: int, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> Response:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    task = await _task(db, journey.id, journey.workspace_id, task_id)
    check_row_version(task.row_version, expected_row_version, "task")
    task.deleted_at = now_utc()
    task.row_version += 1
    db.add(ActivityEvent(workspace_id=journey.workspace_id, journey_id=journey.id, property_id=task.property_id, kind="task_deleted", summary=f"Deleted task: {task.title}", detail={"task_id": str(task.id)}, actor_user_id=auth.user.id))
    await record_audit(db, action="task_deleted", actor_user_id=auth.user.id, workspace_id=journey.workspace_id, subject=str(task.id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/journeys/{journey_id}/tasks/{task_id}/calendar.ics")
async def export_task_ics(journey_id: uuid.UUID, task_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> Response:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    task = await _task(db, journey.id, journey.workspace_id, task_id)
    if task.due_at is None:
        raise HTTPException(status_code=422, detail="Set a due date and time before exporting a calendar file.")
    property_address = (await _task_out(db, task)).property_address
    return Response(content=task_ics(task, property_address), media_type="text/calendar", headers={"Content-Disposition": f'attachment; filename="task-{task.id}.ics"'})