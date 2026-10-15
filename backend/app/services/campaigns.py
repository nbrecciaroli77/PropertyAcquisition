"""Buyer-campaign configuration (U1 / R1).

A buyer campaign is a Journey. Configuration resolves through three explicit layers:
campaign override -> the campaign creator's user default -> system default. Each layer is an
immutable CampaignConfigVersion; "INHERIT" defers to the next layer. Requested and effective
values are reported separately so nothing that is disabled in this build is presented as active.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import CampaignConfigVersion, ConnectorInstance, Journey, Membership, ScheduledJob, User
from app.schemas.campaigns import CampaignSettings
from app.services.matching import EVALUATION_VERSION

INHERIT = "INHERIT"
SETTING_KEYS = (
    "assessment_profile", "activation_at", "timezone", "intake_connection_ref",
    "recipient_user_id", "delivery_mode", "cadence",
)
ASSESSMENT_PROFILES: dict[str, dict[str, Any]] = {
    "HOUSE_V1": {
        "label": "House acquisition v1",
        "campaign_kinds": ("house",),
        "available": True,
        "engine_version": EVALUATION_VERSION,
        "note": "Hard-rule gates, preference fit and evidence coverage are kept separate.",
    },
    "LAND_FEASIBILITY_V1": {
        "label": "Land feasibility v1",
        "campaign_kinds": ("land",),
        "available": False,
        "engine_version": None,
        "note": "Declared for land campaigns. Assessment is implemented in U2; until then matching is skipped and house rules are never borrowed.",
    },
}
KIND_DEFAULT_PROFILE = {"house": "HOUSE_V1", "land": "LAND_FEASIBILITY_V1"}
# Production report workers are a separate activation gate (U7). No worker reads campaign cadence yet.
PRODUCTION_SCHEDULER_ENABLED = False
DEFAULT_CADENCE: dict[str, dict[str, Any]] = {
    "daily": {"enabled": True, "local_time": "07:00", "weekdays": [0, 2, 4]},
    "weekly": {"enabled": True, "local_time": "19:00", "day_of_week": 6},
    "monthly": {"enabled": True, "local_time": "07:00", "day_of_month": 1},
}


def _reject(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": code, "message": message})


def campaign_state_error(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": message})


async def _latest(db: AsyncSession, *, scope: str, workspace_id: uuid.UUID, owner_id: uuid.UUID) -> CampaignConfigVersion | None:
    owner_col = CampaignConfigVersion.journey_id if scope == "campaign" else CampaignConfigVersion.user_id
    return (
        await db.execute(
            select(CampaignConfigVersion)
            .where(CampaignConfigVersion.workspace_id == workspace_id, CampaignConfigVersion.scope == scope, owner_col == owner_id)
            .order_by(CampaignConfigVersion.version_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def list_versions(db: AsyncSession, *, scope: str, workspace_id: uuid.UUID, owner_id: uuid.UUID) -> list[CampaignConfigVersion]:
    owner_col = CampaignConfigVersion.journey_id if scope == "campaign" else CampaignConfigVersion.user_id
    return list(
        (
            await db.execute(
                select(CampaignConfigVersion)
                .where(CampaignConfigVersion.workspace_id == workspace_id, CampaignConfigVersion.scope == scope, owner_col == owner_id)
                .order_by(CampaignConfigVersion.version_no.desc())
            )
        ).scalars().all()
    )


async def _is_member(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return (
        await db.execute(select(Membership.id).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id))
    ).first() is not None


async def validate_settings(
    db: AsyncSession, settings: CampaignSettings, *, workspace_id: uuid.UUID, campaign_kind: str | None
) -> dict[str, Any]:
    """Server-side validation shared by user defaults (campaign_kind=None) and campaign overrides."""
    if settings.assessment_profile != INHERIT:
        profile = ASSESSMENT_PROFILES.get(settings.assessment_profile)
        if profile is None:
            raise _reject("unsupported_assessment_profile", f"Assessment profile {settings.assessment_profile!r} is not supported.")
        if campaign_kind is not None and campaign_kind not in profile["campaign_kinds"]:
            raise _reject(
                "assessment_profile_incompatible",
                f"{settings.assessment_profile} cannot assess a {campaign_kind} campaign.",
            )
    if settings.timezone != INHERIT:
        try:
            ZoneInfo(settings.timezone)
        except Exception as exc:
            raise _reject("invalid_timezone", "Timezone must be a valid IANA timezone.") from exc
    if isinstance(settings.activation_at, datetime) and settings.activation_at.tzinfo is None:
        raise _reject("invalid_activation_at", "Activation time must include a timezone offset.")
    if settings.intake_connection_ref not in (INHERIT, None):
        owned = (
            await db.execute(
                select(ConnectorInstance.id).where(
                    ConnectorInstance.id == settings.intake_connection_ref, ConnectorInstance.workspace_id == workspace_id
                )
            )
        ).first()
        if owned is None:
            raise _reject("intake_connection_not_found", "The intake connection is not part of this workspace.")
    if settings.recipient_user_id != INHERIT and not await _is_member(db, workspace_id, settings.recipient_user_id):
        raise _reject("recipient_not_member", "The recipient must be a member of this workspace.")
    return settings.model_dump(mode="json")


async def save_version(
    db: AsyncSession, *, scope: str, workspace_id: uuid.UUID, owner_id: uuid.UUID, settings: dict[str, Any],
    reason: str, actor_id: uuid.UUID, expected_version: int,
) -> CampaignConfigVersion:
    """Appends an immutable version. A stale expected_version or a concurrent writer is a 409."""
    current = await _latest(db, scope=scope, workspace_id=workspace_id, owner_id=owner_id)
    current_no = current.version_no if current else 0
    if current_no != expected_version:
        raise campaign_state_error("stale_configuration", "This configuration changed in another session. Reload before saving again.")
    row = CampaignConfigVersion(
        workspace_id=workspace_id, scope=scope, version_no=current_no + 1, settings=settings,
        reason=reason.strip(), actor_user_id=actor_id,
        user_id=owner_id if scope == "user_default" else None,
        journey_id=owner_id if scope == "campaign" else None,
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError as exc:
        raise campaign_state_error("stale_configuration", "This configuration changed in another session. Reload before saving again.") from exc
    return row


def _system_defaults(journey: Journey) -> dict[str, Any]:
    return {
        "assessment_profile": KIND_DEFAULT_PROFILE[journey.campaign_kind],
        "activation_at": None,
        "timezone": journey.timezone,
        "intake_connection_ref": None,
        "recipient_user_id": str(journey.created_by),
        "delivery_mode": "separate",
        "cadence": DEFAULT_CADENCE,
    }


def _applicable(key: str, value: Any, journey: Journey) -> bool:
    if key == "assessment_profile":
        return journey.campaign_kind in ASSESSMENT_PROFILES.get(value, {}).get("campaign_kinds", ())
    return True


def _cron(report_type: str, cadence: dict[str, Any]) -> str | None:
    if not cadence.get("enabled"):
        return None
    hour, minute = (int(part) for part in cadence["local_time"].split(":"))
    if report_type == "daily":
        days = ",".join(str((d + 1) % 7) for d in sorted(cadence["weekdays"]))
        return f"{minute} {hour} * * {days}"
    if report_type == "weekly":
        return f"{minute} {hour} * * {(cadence['day_of_week'] + 1) % 7}"
    return f"{minute} {hour} {cadence['day_of_month']} * *"


def _activation_state(activation: str | None, now: datetime) -> str:
    if activation is None:
        return "not_activated"
    return "active" if datetime.fromisoformat(activation) <= now else "pending_activation"


async def resolve(db: AsyncSession, journey: Journey, *, now: datetime | None = None) -> dict[str, Any]:
    moment = now or now_utc()
    campaign_v = await _latest(db, scope="campaign", workspace_id=journey.workspace_id, owner_id=journey.id)
    user_v = await _latest(db, scope="user_default", workspace_id=journey.workspace_id, owner_id=journey.created_by)
    system = _system_defaults(journey)
    settings: dict[str, dict[str, Any]] = {}
    for key in SETTING_KEYS:
        override = (campaign_v.settings if campaign_v else {}).get(key, INHERIT)
        default = (user_v.settings if user_v else {}).get(key, INHERIT)
        note = None
        if override != INHERIT:
            value, source = override, "campaign_override"
        elif default != INHERIT and _applicable(key, default, journey):
            value, source = default, "user_default"
        else:
            value, source = system[key], "system_default"
            if default != INHERIT:
                note = f"Inherited default {default} does not apply to a {journey.campaign_kind} campaign."
        settings[key] = {"override": override, "user_default": default, "requested": value, "source": source, "note": note}

    profile_id = settings["assessment_profile"]["requested"]
    profile = ASSESSMENT_PROFILES[profile_id]
    settings["assessment_profile"].update(
        effective=profile_id if profile["available"] else None,
        state="available" if profile["available"] else "unavailable",
        note=settings["assessment_profile"]["note"] or profile["note"],
    )
    activation = settings["activation_at"]["requested"]
    activation_state = _activation_state(activation, moment)
    settings["activation_at"].update(effective=activation, state=activation_state)
    settings["timezone"].update(effective=settings["timezone"]["requested"], state="ok")

    ref = settings["intake_connection_ref"]["requested"]
    ref_exists = ref is not None and (
        await db.execute(
            select(ConnectorInstance.id).where(ConnectorInstance.id == uuid.UUID(ref), ConnectorInstance.workspace_id == journey.workspace_id)
        )
    ).first() is not None
    settings["intake_connection_ref"].update(
        effective=None,
        state="none" if ref is None else ("reference_only" if ref_exists else "missing"),
        note=None if ref is None else "Recorded as a reference only — live intake connectors are disabled in this build.",
    )

    recipient = uuid.UUID(settings["recipient_user_id"]["requested"])
    member = await _is_member(db, journey.workspace_id, recipient)
    effective_recipient = recipient if member else journey.created_by
    recipient_name = (await db.execute(select(User.display_name).where(User.id == effective_recipient))).scalar_one_or_none()
    settings["recipient_user_id"].update(
        effective=str(effective_recipient), effective_label=recipient_name,
        state="member" if member else "fallback_not_member",
    )

    mode = settings["delivery_mode"]["requested"]
    settings["delivery_mode"].update(
        effective="separate",
        state="ok" if mode == "separate" else "unsupported_until_u6",
        note=None if mode == "separate" else "Combined delivery is not available yet; each campaign is delivered separately.",
    )

    cadence = settings["cadence"]["requested"]
    jobs = (
        await db.execute(select(ScheduledJob).where(ScheduledJob.workspace_id == journey.workspace_id, ScheduledJob.job_kind == "report_release"))
    ).scalars().all()
    schedule = []
    for report_type in ("daily", "weekly", "monthly"):
        job = next((j for j in jobs if j.config.get("report_type") == report_type), None)
        requested_cron = _cron(report_type, cadence[report_type])
        if not journey.campaign_enabled:
            sync_state = "campaign_disabled"
        elif requested_cron is None:
            sync_state = "cadence_off"
        elif activation_state != "active":
            sync_state = "awaiting_activation"
        elif not PRODUCTION_SCHEDULER_ENABLED:
            sync_state = "worker_disabled"
        else:
            sync_state = "in_sync" if job and job.enabled and job.schedule_cron == requested_cron else "out_of_sync"
        schedule.append({
            "report_type": report_type,
            "requested_cron": requested_cron,
            "configured_cron": job.schedule_cron if job else None,
            "configured_enabled": bool(job and job.enabled),
            "config_drift": bool(requested_cron and (job is None or job.schedule_cron != requested_cron)),
            "effective_cron": None,
            "next_due_at": None,
            "sync_state": sync_state,
        })
    settings["cadence"].update(effective=None, state="not_scheduled")

    return {
        "journey_id": journey.id,
        "campaign_kind": journey.campaign_kind,
        "campaign_enabled": journey.campaign_enabled,
        "settings_owner_user_id": journey.created_by,
        "campaign_version": campaign_v.version_no if campaign_v else 0,
        "user_default_version": user_v.version_no if user_v else 0,
        "settings": settings,
        "schedule": schedule,
        "production_scheduler_enabled": PRODUCTION_SCHEDULER_ENABLED,
        "resolved_at": moment,
    }


async def effective_timezone(db: AsyncSession, journey: Journey) -> str:
    resolved = await resolve(db, journey)
    return str(resolved["settings"]["timezone"]["effective"])


async def assessment_profile(db: AsyncSession, journey: Journey) -> tuple[str, bool]:
    """(profile id, available). An unavailable profile means: do not evaluate, never fall back."""
    resolved = await resolve(db, journey)
    entry = resolved["settings"]["assessment_profile"]
    return str(entry["requested"]), entry["state"] == "available"


def require_accepting_intake(journey: Journey) -> None:
    if not journey.campaign_enabled:
        raise campaign_state_error("campaign_disabled", "This campaign is disabled and is not accepting new evidence.")


async def require_production_allowed(db: AsyncSession, journey: Journey, *, period_end: datetime, now: datetime) -> datetime:
    """Production runs need an enabled, activated campaign and a period that ends after activation."""
    if not journey.campaign_enabled:
        raise campaign_state_error("campaign_disabled", "This campaign is disabled; production reports are blocked.")
    resolved = await resolve(db, journey, now=now)
    activation = resolved["settings"]["activation_at"]["effective"]
    if activation is None:
        raise campaign_state_error("campaign_not_activated", "Set an activation time before producing scheduled reports.")
    activated_at = datetime.fromisoformat(activation)
    if activated_at > now:
        raise campaign_state_error("campaign_not_activated", "This campaign has not reached its activation time yet.")
    if period_end <= activated_at:
        raise campaign_state_error("period_before_activation", "Production reports cannot cover a period before activation.")
    return activated_at
