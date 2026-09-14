"""Cooling-off account/workspace deletion workflow. Execution is manual/test-only; no
production deletion scheduler is activated. Never touches another workspace's data."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext
from app.core.security import now_utc, verify_password
from app.db.models import AuthSession, DeletionRequest, LoginAttempt, Membership, User, Workspace
from app.services.exports import purge_exports_for_user
from app.services.outbox import record_audit

COOLOFF_HOURS = 72
CONFIRMATION_WORD = "DELETE"


async def _membership_count(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    return int(
        (await db.execute(select(func.count()).select_from(Membership).where(Membership.workspace_id == workspace_id))).scalar_one()
    )


async def _is_sole_owner(db: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    membership = (
        await db.execute(select(Membership).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id))
    ).scalar_one_or_none()
    if membership is None or membership.role != "owner":
        return False
    return await _membership_count(db, workspace_id) == 1


async def create_deletion_request(
    db: AsyncSession,
    *,
    auth: AuthContext,
    request_type: str,
    password: str,
    typed_confirmation: str,
    target_workspace_id: uuid.UUID | None,
) -> DeletionRequest:
    if typed_confirmation.strip() != CONFIRMATION_WORD:
        raise HTTPException(status_code=422, detail={"code": "confirmation_mismatch", "message": f'Type "{CONFIRMATION_WORD}" to confirm.'})
    if not verify_password(password, auth.user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "reauthentication_failed", "message": "Your password does not match. Re-enter it to continue."})

    existing = (
        await db.execute(
            select(DeletionRequest).where(
                DeletionRequest.requested_by_user_id == auth.user.id,
                DeletionRequest.request_type == request_type,
                DeletionRequest.state == "pending_cooloff",
                DeletionRequest.target_workspace_id == target_workspace_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    detail: dict[str, Any] = {}
    scope_workspace_id: uuid.UUID | None = None
    if request_type == "leave_workspace":
        if target_workspace_id is None:
            raise HTTPException(status_code=422, detail="target_workspace_id is required to leave a workspace.")
        membership = (
            await db.execute(select(Membership).where(Membership.workspace_id == target_workspace_id, Membership.user_id == auth.user.id))
        ).scalar_one_or_none()
        if membership is None:
            raise HTTPException(status_code=404, detail="Workspace membership not found")
        if membership.role == "owner":
            member_count = await _membership_count(db, target_workspace_id)
            if member_count > 1:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "ownership_transfer_required", "message": "Transfer ownership to another member before you can leave this workspace."},
                )
            raise HTTPException(
                status_code=422,
                detail={"code": "sole_owner_cannot_leave", "message": "You are the only member. Delete this workspace or delete your account instead of leaving."},
            )
        scope_workspace_id = target_workspace_id
        detail = {"consequence": "You will lose access to this workspace. Its data is not deleted.", "workspace_id": str(target_workspace_id)}
    elif request_type == "delete_account":
        owned = (await db.execute(select(Membership).where(Membership.user_id == auth.user.id, Membership.role == "owner"))).scalars().all()
        blocking = [str(m.workspace_id) for m in owned if await _membership_count(db, m.workspace_id) > 1]
        if blocking:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "ownership_transfer_required",
                    "message": "Transfer ownership of your shared workspace(s) before deleting your account.",
                    "workspace_ids": blocking,
                },
            )
        detail = {
            "consequence": "Your account is permanently deleted, every session is revoked, and any workspace you solely own is deleted with its data.",
            "solely_owned_workspaces": [str(m.workspace_id) for m in owned],
        }
    elif request_type == "delete_workspace":
        if target_workspace_id is None:
            raise HTTPException(status_code=422, detail="target_workspace_id is required to delete a workspace.")
        if not await _is_sole_owner(db, auth.user.id, target_workspace_id):
            raise HTTPException(
                status_code=422,
                detail={"code": "ownership_transfer_required", "message": "Only the sole owner of a workspace with no other members can delete it."},
            )
        scope_workspace_id = target_workspace_id
        detail = {
            "consequence": "This workspace and all of its data — properties, brief, tasks, notifications and reports — is permanently deleted.",
            "workspace_id": str(target_workspace_id),
        }
    else:
        raise HTTPException(status_code=422, detail="Unknown deletion request type")

    request = DeletionRequest(
        requested_by_user_id=auth.user.id, request_type=request_type, target_workspace_id=scope_workspace_id,
        state="pending_cooloff", detail=detail, scheduled_execute_at=now_utc() + timedelta(hours=COOLOFF_HOURS),
    )
    db.add(request)
    await db.flush()
    await record_audit(
        db, action="deletion.requested", actor_user_id=auth.user.id, workspace_id=scope_workspace_id,
        subject=str(request.id), detail={"request_type": request_type},
    )
    return request


async def cancel_deletion_request(db: AsyncSession, *, auth: AuthContext, request_id: uuid.UUID) -> DeletionRequest:
    request = (
        await db.execute(select(DeletionRequest).where(DeletionRequest.id == request_id, DeletionRequest.requested_by_user_id == auth.user.id))
    ).scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    if request.state != "pending_cooloff":
        raise HTTPException(status_code=422, detail="Only a pending request can be cancelled.")
    request.state = "cancelled"
    request.cancelled_at = now_utc()
    await record_audit(db, action="deletion.cancelled", actor_user_id=auth.user.id, subject=str(request.id))
    return request


async def _revoke_sessions(db: AsyncSession, user_id: uuid.UUID, reason: str) -> None:
    sessions = (await db.execute(select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)))).scalars().all()
    for s in sessions:
        s.revoked_at = now_utc()
        s.revoked_reason = reason


async def _delete_workspace_cascade(db: AsyncSession, workspace_id: uuid.UUID) -> None:
    workspace = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one_or_none()
    if workspace is not None:
        await db.delete(workspace)


async def _execute_request(db: AsyncSession, request: DeletionRequest) -> None:
    request.state = "processing"
    await db.flush()
    if request.request_type == "leave_workspace":
        await db.execute(delete(Membership).where(Membership.workspace_id == request.target_workspace_id, Membership.user_id == request.requested_by_user_id))
    elif request.request_type == "delete_workspace":
        if request.target_workspace_id is not None and await _is_sole_owner(db, request.requested_by_user_id, request.target_workspace_id):
            await _delete_workspace_cascade(db, request.target_workspace_id)
    elif request.request_type == "delete_account":
        user = (await db.execute(select(User).where(User.id == request.requested_by_user_id))).scalar_one_or_none()
        if user is not None:
            owned = (await db.execute(select(Membership).where(Membership.user_id == user.id, Membership.role == "owner"))).scalars().all()
            for m in owned:
                if await _membership_count(db, m.workspace_id) == 1:
                    await _delete_workspace_cascade(db, m.workspace_id)
            await db.execute(delete(Membership).where(Membership.user_id == user.id))
            await _revoke_sessions(db, user.id, "account_deletion")
            await purge_exports_for_user(db, user.id)
            await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier == f"email:{user.email}"))
            user.deleted_at = now_utc()
            user.email = f"deleted-{user.id}@deleted.invalid"
            user.display_name = "Deleted user"
            user.password_hash = "!" + uuid.uuid4().hex
            other_pending = (
                await db.execute(
                    select(DeletionRequest).where(
                        DeletionRequest.requested_by_user_id == user.id, DeletionRequest.state == "pending_cooloff", DeletionRequest.id != request.id
                    )
                )
            ).scalars().all()
            for other in other_pending:
                other.state = "cancelled"
                other.cancelled_at = now_utc()
    request.state = "completed"
    request.executed_at = now_utc()
    await record_audit(db, action="deletion.executed", workspace_id=request.target_workspace_id, subject=str(request.id), detail={"request_type": request.request_type})


async def process_due_deletions(db: AsyncSession, *, now: datetime | None = None) -> dict[str, int]:
    moment = now or now_utc()
    due = (
        await db.execute(select(DeletionRequest).where(DeletionRequest.state == "pending_cooloff", DeletionRequest.scheduled_execute_at <= moment))
    ).scalars().all()
    processed = 0
    for request in due:
        try:
            await _execute_request(db, request)
            processed += 1
        except Exception as exc:
            request.state = "failed"
            request.failure_reason = str(exc)[:400]
    return {"processed": processed, "checked": len(due)}
