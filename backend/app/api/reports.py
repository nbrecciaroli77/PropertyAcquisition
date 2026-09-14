import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.db.base import get_db
from app.db.models import REPORT_TYPES, ReportPreference, ReportRun
from app.schemas.reports import (
    ReportGenerateRequest,
    ReportPreferenceOut,
    ReportPreferencesOut,
    ReportPreferenceUpdate,
    ReportRunOut,
)
from app.services.notifications import reject_email_channel
from app.services.reports import generate_report

router = APIRouter(tags=["reports"])

DEFAULTS: dict[str, dict[str, object]] = {
    "daily": {"local_time": "07:00", "weekdays": [0, 1, 2, 3, 4, 5, 6], "day_of_week": None, "day_of_month": None},
    "weekly": {"local_time": "18:00", "weekdays": [], "day_of_week": 6, "day_of_month": None},
    "monthly": {"local_time": "07:00", "weekdays": [], "day_of_week": None, "day_of_month": 1},
}


def _run_out(run: ReportRun) -> ReportRunOut:
    return ReportRunOut(
        id=run.id, journey_id=run.journey_id, report_type=run.report_type, kind=run.kind,
        release_state=run.release_state, idempotency_key=run.idempotency_key, period_start=run.period_start,
        period_end=run.period_end, cutoff_at=run.cutoff_at, timezone=run.timezone,
        generation_version=run.generation_version, is_partial_period=run.is_partial_period,
        failure_reason=run.failure_reason, generated_at=run.generated_at, snapshot=run.snapshot,
        detail=run.detail, created_at=run.created_at,
    )


def _validate_report_type(report_type: str) -> None:
    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=404, detail="Report type not found")


@router.post("/journeys/{journey_id}/reports/{report_type}/generate", response_model=ReportRunOut)
async def generate(
    journey_id: uuid.UUID, report_type: str, body: ReportGenerateRequest,
    auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db),
) -> ReportRunOut:
    _validate_report_type(report_type)
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    run = await generate_report(
        db, journey=journey, report_type=report_type, release_kind=body.release_kind, requested_by_user_id=auth.user.id,
        year=body.year, month=body.month, week_start=body.week_start,
    )
    await db.commit()
    await db.refresh(run)
    return _run_out(run)


@router.get("/journeys/{journey_id}/reports", response_model=list[ReportRunOut])
async def list_reports(
    journey_id: uuid.UUID, report_type: str | None = Query(default=None),
    auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db),
) -> list[ReportRunOut]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    query = select(ReportRun).where(ReportRun.workspace_id == journey.workspace_id, ReportRun.journey_id == journey.id)
    if report_type:
        _validate_report_type(report_type)
        query = query.where(ReportRun.report_type == report_type)
    rows = (await db.execute(query.order_by(ReportRun.created_at.desc()).limit(50))).scalars().all()
    return [_run_out(r) for r in rows]


@router.get("/journeys/{journey_id}/reports/{report_run_id}", response_model=ReportRunOut)
async def get_report(
    journey_id: uuid.UUID, report_run_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> ReportRunOut:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    run = (
        await db.execute(
            select(ReportRun).where(ReportRun.id == report_run_id, ReportRun.workspace_id == journey.workspace_id, ReportRun.journey_id == journey.id)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _run_out(run)


def _pref_out(report_type: str, pref: ReportPreference | None) -> ReportPreferenceOut:
    defaults = DEFAULTS[report_type]
    if pref is None:
        return ReportPreferenceOut(
            report_type=report_type, enabled=False, local_time=defaults["local_time"], weekdays=defaults["weekdays"],
            day_of_week=defaults["day_of_week"], day_of_month=defaults["day_of_month"], timezone="Australia/Perth",
            requested_channel="in_app", effective_channel="in_app",
        )
    return ReportPreferenceOut(
        report_type=report_type, enabled=pref.enabled, local_time=pref.local_time, weekdays=pref.weekdays,
        day_of_week=pref.day_of_week, day_of_month=pref.day_of_month, timezone=pref.timezone,
        requested_channel=pref.requested_channel, effective_channel=pref.effective_channel,
    )


async def _get_pref(db: AsyncSession, auth: AuthContext, report_type: str) -> ReportPreference | None:
    return (
        await db.execute(
            select(ReportPreference).where(
                ReportPreference.workspace_id == auth.workspace.id, ReportPreference.user_id == auth.user.id, ReportPreference.report_type == report_type
            )
        )
    ).scalar_one_or_none()


@router.get("/reports/preferences", response_model=ReportPreferencesOut)
async def report_preferences(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> ReportPreferencesOut:
    return ReportPreferencesOut(
        daily=_pref_out("daily", await _get_pref(db, auth, "daily")),
        weekly=_pref_out("weekly", await _get_pref(db, auth, "weekly")),
        monthly=_pref_out("monthly", await _get_pref(db, auth, "monthly")),
    )


@router.put("/reports/preferences/{report_type}", response_model=ReportPreferenceOut)
async def update_report_preference(
    report_type: str, body: ReportPreferenceUpdate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> ReportPreferenceOut:
    _validate_report_type(report_type)
    reject_email_channel(body.requested_channel)
    try:
        __import__("zoneinfo").ZoneInfo(body.timezone)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Timezone must be a valid IANA timezone.") from exc
    pref = await _get_pref(db, auth, report_type)
    if pref is None:
        pref = ReportPreference(workspace_id=auth.workspace.id, user_id=auth.user.id, report_type=report_type)
        db.add(pref)
    pref.enabled, pref.local_time, pref.weekdays = body.enabled, body.local_time, body.weekdays
    pref.day_of_week, pref.day_of_month, pref.timezone = body.day_of_week, body.day_of_month, body.timezone
    pref.requested_channel = body.requested_channel
    pref.effective_channel = body.requested_channel if body.requested_channel == "in_app" else "off"
    await db.commit()
    return _pref_out(report_type, pref)
