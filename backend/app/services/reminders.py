"""Manual, idempotent reminder processing. No scheduler is activated."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import JobRun, PropertyTask, ScheduledJob, Workspace
from app.services.notifications import create_notification_event, due_soon_minutes


async def _job(db: AsyncSession, workspace_id: uuid.UUID) -> ScheduledJob:
    job = (
        await db.execute(
            select(ScheduledJob).where(
                ScheduledJob.workspace_id == workspace_id,
                ScheduledJob.job_kind == "reminder_processing",
            )
        )
    ).scalar_one_or_none()
    if job is None:
        job = ScheduledJob(
            workspace_id=workspace_id,
            job_kind="reminder_processing",
            schedule_cron="manual-only",
            timezone="UTC",
            enabled=False,
            config={"manual_only": True},
        )
        db.add(job)
        await db.flush()
    return job


async def process_workspace_reminders(
    db: AsyncSession, workspace_id: uuid.UUID, *, now: datetime | None = None
) -> dict[str, int]:
    moment = now or now_utc()
    job = await _job(db, workspace_id)
    run = JobRun(workspace_id=workspace_id, job_id=job.id, run_state="running", started_at=moment, detail={})
    db.add(run)
    await db.flush()
    created = {"due_soon": 0, "overdue": 0, "reminder": 0}
    tasks = (
        await db.execute(
            select(PropertyTask).where(
                PropertyTask.workspace_id == workspace_id,
                PropertyTask.status == "open",
                PropertyTask.done.is_(False),
                PropertyTask.deleted_at.is_(None),
                PropertyTask.due_at.is_not(None),
            )
        )
    ).scalars().all()
    for task in tasks:
        assert task.due_at is not None
        target_ids = {task.assignee_user_id or task.created_by}
        link = f"/app/tasks?task={task.id}"
        if task.reminder_offset_minutes and task.due_at - timedelta(minutes=task.reminder_offset_minutes) <= moment < task.due_at:
            await create_notification_event(
                db, workspace_id=workspace_id, category="reminder", fingerprint=f"task:{task.id}:reminder",
                title=f"Reminder: {task.title}", message="Your task reminder is due.", safe_deep_link=link,
                priority="normal", property_id=task.property_id, task_id=task.id, recipient_ids=target_ids,
                evidence_ref={"due_at": task.due_at.isoformat()}, now=moment,
            )
            created["reminder"] += 1
        if task.due_at <= moment:
            await create_notification_event(
                db, workspace_id=workspace_id, category="task_overdue", fingerprint=f"task:{task.id}:overdue",
                title=f"Task overdue: {task.title}", message="This task is past its due time.", safe_deep_link=link,
                priority="high", property_id=task.property_id, task_id=task.id, recipient_ids=target_ids,
                evidence_ref={"due_at": task.due_at.isoformat()}, now=moment,
            )
            created["overdue"] += 1
            continue
        # Due-soon timing is recipient-specific; events are created only for recipients whose
        # global preference includes the remaining time.
        from app.db.models import Membership, User
        members = (
            await db.execute(
                select(User).join(Membership, Membership.user_id == User.id).where(
                    Membership.workspace_id == workspace_id, User.id.in_(target_ids)
                )
            )
        ).scalars().all()
        eligible = {
            user.id for user in members
            if task.due_at <= moment + timedelta(minutes=await due_soon_minutes(db, workspace_id=workspace_id, user=user))
        }
        if eligible:
            await create_notification_event(
                db, workspace_id=workspace_id, category="task_due_soon", fingerprint=f"task:{task.id}:due-soon",
                title=f"Task due soon: {task.title}", message="This task is approaching its due time.", safe_deep_link=link,
                priority="high", property_id=task.property_id, task_id=task.id, recipient_ids=eligible,
                evidence_ref={"due_at": task.due_at.isoformat()}, now=moment,
            )
            created["due_soon"] += 1
    run.run_state = "completed"
    run.finished_at = now_utc()
    run.detail = {**created, "tasks_checked": len(tasks), "manual_only": True}
    return created


async def process_all_workspace_reminders(db: AsyncSession, *, now: datetime | None = None) -> dict[str, int]:
    totals = {"workspaces": 0, "due_soon": 0, "overdue": 0, "reminder": 0}
    for workspace_id in (await db.execute(select(Workspace.id))).scalars():
        outcome = await process_workspace_reminders(db, workspace_id, now=now)
        totals["workspaces"] += 1
        for key, value in outcome.items():
            totals[key] += value
    return totals