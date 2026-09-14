import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import NotificationEvent, NotificationPreference, Property, RecipientNotification
from app.schemas.notifications import (
    CategoryPreferenceUpdate,
    GlobalPreferenceUpdate,
    NotificationListOut,
    NotificationOut,
    NotificationStateUpdate,
    NotificationPreferenceOut,
    PreferencesOut,
)
from app.services.notifications import CATEGORY_LABELS as SERVICE_CATEGORY_LABELS, DEFAULT_DUE_SOON_MINUTES, reject_email_channel, unread_count


router = APIRouter(prefix="/notifications", tags=["notifications"])


def _pref_out(pref: NotificationPreference | None, category: str | None, timezone: str) -> NotificationPreferenceOut:
    return NotificationPreferenceOut(
        category=category, requested_channel=pref.requested_channel if pref else "in_app",
        effective_channel=pref.effective_channel if pref else "in_app", global_in_app_enabled=pref.in_app_enabled if pref else True,
        quiet_hours_start=pref.quiet_hours_start if pref else None, quiet_hours_end=pref.quiet_hours_end if pref else None,
        timezone=pref.timezone if pref and pref.timezone else timezone, due_soon_minutes=pref.due_soon_minutes if pref and pref.due_soon_minutes else DEFAULT_DUE_SOON_MINUTES,
        report_daily_enabled=pref.report_daily_enabled if pref else False, report_weekly_enabled=pref.report_weekly_enabled if pref else False,
        report_monthly_enabled=pref.report_monthly_enabled if pref else False, report_preferences_active=False, email_provider_connected=False,
    )


async def _pref(db: AsyncSession, auth: AuthContext, scope_key: str) -> NotificationPreference | None:
    return (await db.execute(select(NotificationPreference).where(NotificationPreference.workspace_id == auth.workspace.id, NotificationPreference.user_id == auth.user.id, NotificationPreference.scope_key == scope_key))).scalar_one_or_none()


@router.get("", response_model=NotificationListOut)
async def list_notifications(unread_only: bool = False, category: str | None = None, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> NotificationListOut:
    query = select(RecipientNotification, NotificationEvent, Property).join(NotificationEvent, NotificationEvent.id == RecipientNotification.notification_event_id).outerjoin(Property, Property.id == NotificationEvent.property_id).where(RecipientNotification.workspace_id == auth.workspace.id, RecipientNotification.recipient_user_id == auth.user.id, RecipientNotification.dismissed_at.is_(None)).order_by(RecipientNotification.created_at.desc())
    if unread_only:
        query = query.where(RecipientNotification.read_at.is_(None))
    if category:
        query = query.where(NotificationEvent.category == category)
    rows = (await db.execute(query)).all()
    now = now_utc()
    return NotificationListOut(items=[NotificationOut(id=inbox.id, event_id=event.id, category=event.category, title=event.title, message=event.message, priority=event.priority, safe_deep_link=event.safe_deep_link, property_id=event.property_id, property_address=f"{prop.address_line}, {prop.suburb} {prop.state}" if prop else None, property_image_url=prop.image_url if prop else None, task_id=event.task_id, source_event_id=event.source_event_id, report_run_id=event.report_run_id, evidence_ref=event.evidence_ref, created_at=inbox.created_at, read_at=inbox.read_at, dismissed_at=inbox.dismissed_at, expires_at=event.expires_at, is_expired=bool(event.expires_at and event.expires_at <= now)) for inbox, event, prop in rows], unread_count=await unread_count(db, auth.workspace.id, auth.user.id))


async def _inbox(db: AsyncSession, auth: AuthContext, inbox_id: uuid.UUID) -> RecipientNotification:
    item = (await db.execute(select(RecipientNotification).where(RecipientNotification.id == inbox_id, RecipientNotification.workspace_id == auth.workspace.id, RecipientNotification.recipient_user_id == auth.user.id))).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return item


@router.patch("/{inbox_id}", response_model=NotificationListOut)
async def update_notification(inbox_id: uuid.UUID, body: NotificationStateUpdate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> NotificationListOut:
    item = await _inbox(db, auth, inbox_id)
    if body.read is not None:
        item.read_at = now_utc() if body.read else None
    if body.dismissed is not None:
        item.dismissed_at = now_utc() if body.dismissed else None
    await db.commit()
    return await list_notifications(auth=auth, db=db)


@router.post("/mark-all-read", response_model=NotificationListOut)
async def mark_all_read(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> NotificationListOut:
    rows = (await db.execute(select(RecipientNotification).where(RecipientNotification.workspace_id == auth.workspace.id, RecipientNotification.recipient_user_id == auth.user.id, RecipientNotification.read_at.is_(None), RecipientNotification.dismissed_at.is_(None)))).scalars()
    now = now_utc()
    for item in rows:
        item.read_at = now
    await db.commit()
    return await list_notifications(auth=auth, db=db)


@router.get("/preferences", response_model=PreferencesOut)
async def preferences(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> PreferencesOut:
    global_pref = await _pref(db, auth, "global")
    categories = []
    for category in SERVICE_CATEGORY_LABELS:
        categories.append(_pref_out(await _pref(db, auth, f"category:{category}"), category, auth.user.timezone))
    return PreferencesOut(global_settings=_pref_out(global_pref, None, auth.user.timezone), categories=categories)


@router.put("/preferences/global", response_model=NotificationPreferenceOut)
async def update_global_preferences(body: GlobalPreferenceUpdate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> NotificationPreferenceOut:
    try:
        __import__("zoneinfo").ZoneInfo(body.timezone)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Timezone must be a valid IANA timezone.") from exc
    pref = await _pref(db, auth, "global")
    if pref is None:
        pref = NotificationPreference(workspace_id=auth.workspace.id, user_id=auth.user.id, scope_key="global", category=None)
        db.add(pref)
    pref.in_app_enabled, pref.quiet_hours_start, pref.quiet_hours_end = body.in_app_enabled, body.quiet_hours_start, body.quiet_hours_end
    pref.timezone, pref.due_soon_minutes = body.timezone, body.due_soon_minutes
    pref.report_daily_enabled, pref.report_weekly_enabled, pref.report_monthly_enabled = body.report_daily_enabled, body.report_weekly_enabled, body.report_monthly_enabled
    await db.commit()
    return _pref_out(pref, None, auth.user.timezone)


@router.put("/preferences/{category}", response_model=NotificationPreferenceOut)
async def update_category_preference(category: str, body: CategoryPreferenceUpdate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> NotificationPreferenceOut:
    if category not in SERVICE_CATEGORY_LABELS:
        raise HTTPException(status_code=404, detail="Notification category not found")
    reject_email_channel(body.requested_channel)
    pref = await _pref(db, auth, f"category:{category}")
    if pref is None:
        pref = NotificationPreference(workspace_id=auth.workspace.id, user_id=auth.user.id, scope_key=f"category:{category}", category=category)
        db.add(pref)
    pref.requested_channel = body.requested_channel
    pref.effective_channel = body.requested_channel
    await db.commit()
    return _pref_out(pref, category, auth.user.timezone)