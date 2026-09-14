"""Deterministic, in-app-only notification delivery. No email or HTTP calls occur here."""
from __future__ import annotations

import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import (
    Membership,
    NotificationDeliveryAttempt,
    NotificationEvent,
    NotificationPreference,
    RecipientNotification,
    User,
)


REPORT_CATEGORIES = {"digest_ready", "weekly_report_ready", "monthly_report_ready"}
CRITICAL_CATEGORIES = {"critical_service"}
CATEGORY_LABELS = {
    "new_property": "New property",
    "material_property_change": "Material property change",
    "price_change": "Price change",
    "inspection_change": "Home open or inspection change",
    "evidence_gap": "Important evidence gap",
    "duplicate_review": "Duplicate requiring review",
    "task_assigned": "Task assigned",
    "task_due_soon": "Task due soon",
    "task_overdue": "Task overdue",
    "reminder": "Reminder",
    "source_processing_failure": "Source or processing failure",
    "digest_ready": "Digest ready",
    "weekly_report_ready": "Weekly report ready",
    "monthly_report_ready": "Monthly report ready",
}
DEFAULT_DUE_SOON_MINUTES = 24 * 60


def _safe_link(path: str) -> str:
    if not path.startswith("/app/") or path.startswith("//"):
        raise ValueError("Notification links must be internal application paths")
    return path


async def _preference(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, scope_key: str
) -> NotificationPreference | None:
    return (
        await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.workspace_id == workspace_id,
                NotificationPreference.user_id == user_id,
                NotificationPreference.scope_key == scope_key,
            )
        )
    ).scalar_one_or_none()


def _in_quiet_hours(moment: datetime, timezone: str, start: str | None, end: str | None) -> bool:
    if not start or not end or start == end:
        return False
    try:
        local = moment.astimezone(ZoneInfo(timezone)).time()
    except Exception:
        return False
    start_time, end_time = time.fromisoformat(start), time.fromisoformat(end)
    return start_time <= local < end_time if start_time < end_time else local >= start_time or local < end_time


async def effective_in_app_enabled(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user: User,
    category: str,
    now: datetime | None = None,
) -> bool:
    if category in CRITICAL_CATEGORIES:
        return True
    global_pref = await _preference(db, workspace_id, user.id, "global")
    category_pref = await _preference(db, workspace_id, user.id, f"category:{category}")
    if global_pref and not global_pref.in_app_enabled:
        return False
    if category_pref and category_pref.effective_channel == "off":
        return False
    moment = now or now_utc()
    timezone = (global_pref.timezone if global_pref and global_pref.timezone else user.timezone)
    return not _in_quiet_hours(
        moment,
        timezone,
        global_pref.quiet_hours_start if global_pref else None,
        global_pref.quiet_hours_end if global_pref else None,
    )


async def due_soon_minutes(
    db: AsyncSession, *, workspace_id: uuid.UUID, user: User
) -> int:
    pref = await _preference(db, workspace_id, user.id, "global")
    return pref.due_soon_minutes if pref and pref.due_soon_minutes else DEFAULT_DUE_SOON_MINUTES


async def create_notification_event(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    category: str,
    fingerprint: str,
    title: str,
    message: str,
    safe_deep_link: str,
    priority: str = "normal",
    property_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    source_event_id: uuid.UUID | None = None,
    report_run_id: uuid.UUID | None = None,
    evidence_ref: dict[str, object] | None = None,
    expires_at: datetime | None = None,
    recipient_ids: set[uuid.UUID] | None = None,
    now: datetime | None = None,
) -> NotificationEvent:
    """Create one event per workspace fingerprint and eligible in-app inbox rows.

    A replay returns the existing event and may fill an inbox row that was previously
    suppressed by quiet hours. It never creates duplicate events or deliveries.
    """
    path = _safe_link(safe_deep_link)
    event = (
        await db.execute(
            select(NotificationEvent).where(
                NotificationEvent.workspace_id == workspace_id,
                NotificationEvent.event_fingerprint == fingerprint,
            )
        )
    ).scalar_one_or_none()
    if event is None:
        try:
            async with db.begin_nested():
                event = NotificationEvent(
                    workspace_id=workspace_id,
                    category=category,
                    event_fingerprint=fingerprint,
                    title=title,
                    message=message,
                    safe_deep_link=path,
                    priority=priority,
                    property_id=property_id,
                    task_id=task_id,
                    source_event_id=source_event_id,
                    report_run_id=report_run_id,
                    evidence_ref=evidence_ref or {},
                    expires_at=expires_at,
                )
                db.add(event)
                await db.flush()
        except IntegrityError:
            event = (
                await db.execute(
                    select(NotificationEvent).where(
                        NotificationEvent.workspace_id == workspace_id,
                        NotificationEvent.event_fingerprint == fingerprint,
                    )
                )
            ).scalar_one()

    members = (
        await db.execute(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.workspace_id == workspace_id, Membership.role.in_(("owner", "editor", "viewer")))
        )
    ).scalars().all()
    selected = [member for member in members if recipient_ids is None or member.id in recipient_ids]
    for member in selected:
        if not await effective_in_app_enabled(
            db, workspace_id=workspace_id, user=member, category=category, now=now
        ):
            continue
        inbox = (
            await db.execute(
                select(RecipientNotification).where(
                    RecipientNotification.notification_event_id == event.id,
                    RecipientNotification.recipient_user_id == member.id,
                )
            )
        ).scalar_one_or_none()
        if inbox is not None:
            continue
        inbox = RecipientNotification(
            workspace_id=workspace_id,
            notification_event_id=event.id,
            recipient_user_id=member.id,
        )
        db.add(inbox)
        await db.flush()
        db.add(
            NotificationDeliveryAttempt(
                workspace_id=workspace_id,
                recipient_notification_id=inbox.id,
                channel="in_app",
                delivery_state="delivered",
                detail="Durable in-app inbox item created.",
            )
        )
    return event


async def unread_count(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(RecipientNotification)
                .join(NotificationEvent, NotificationEvent.id == RecipientNotification.notification_event_id)
                .where(
                    RecipientNotification.workspace_id == workspace_id,
                    RecipientNotification.recipient_user_id == user_id,
                    RecipientNotification.read_at.is_(None),
                    RecipientNotification.dismissed_at.is_(None),
                    (NotificationEvent.expires_at.is_(None) | (NotificationEvent.expires_at > now_utc())),
                )
            )
        ).scalar_one()
    )


def reject_email_channel(channel: str) -> None:
    if channel in {"email", "both"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "email_provider_not_connected", "message": "Email provider not connected."},
        )