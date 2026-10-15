"""Buyer-campaign configuration API. Tenant scope is always derived from the authenticated
membership; a campaign in another workspace is indistinguishable from a missing one (404)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.db.base import get_db
from app.db.models import CampaignConfigVersion, ReportRun, ReportRunLegacyMapping
from app.schemas.campaigns import (
    AssessmentProfileOut,
    CampaignConfigOut,
    CampaignConfigVersionOut,
    CampaignSettingsSave,
    ReportLocationOut,
    UserDefaultsOut,
)
from app.services.campaigns import (
    ASSESSMENT_PROFILES,
    _latest,
    list_versions,
    resolve,
    save_version,
    validate_settings,
)
from app.services.outbox import record_audit

router = APIRouter(tags=["campaigns"])


def _version_out(v: CampaignConfigVersion) -> CampaignConfigVersionOut:
    return CampaignConfigVersionOut(
        id=v.id, scope=v.scope, version_no=v.version_no, settings=v.settings, reason=v.reason,
        actor_user_id=v.actor_user_id, created_at=v.created_at,
    )


@router.get("/assessment-profiles", response_model=list[AssessmentProfileOut])
async def assessment_profiles(auth: AuthContext = Depends(get_auth)) -> list[AssessmentProfileOut]:
    return [
        AssessmentProfileOut(id=pid, label=p["label"], campaign_kinds=list(p["campaign_kinds"]), available=p["available"], engine_version=p["engine_version"], note=p["note"])
        for pid, p in ASSESSMENT_PROFILES.items()
    ]


@router.get("/journeys/{journey_id}/campaign", response_model=CampaignConfigOut)
async def campaign_config(journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> CampaignConfigOut:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    return CampaignConfigOut.model_validate(await resolve(db, journey))


@router.put("/journeys/{journey_id}/campaign/overrides", response_model=CampaignConfigOut)
async def save_overrides(
    journey_id: uuid.UUID, body: CampaignSettingsSave, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> CampaignConfigOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    settings = await validate_settings(db, body.settings, workspace_id=journey.workspace_id, campaign_kind=journey.campaign_kind)
    row = await save_version(
        db, scope="campaign", workspace_id=journey.workspace_id, owner_id=journey.id, settings=settings,
        reason=body.reason, actor_id=auth.user.id, expected_version=body.expected_version,
    )
    await record_audit(db, action="campaign.config_saved", actor_user_id=auth.user.id, workspace_id=journey.workspace_id, subject=str(journey.id), detail={"version_no": row.version_no})
    await db.commit()
    return CampaignConfigOut.model_validate(await resolve(db, journey))


@router.get("/journeys/{journey_id}/campaign/versions", response_model=list[CampaignConfigVersionOut])
async def campaign_versions(journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> list[CampaignConfigVersionOut]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    rows = await list_versions(db, scope="campaign", workspace_id=journey.workspace_id, owner_id=journey.id)
    return [_version_out(v) for v in rows]


@router.get("/campaign-defaults", response_model=UserDefaultsOut)
async def my_defaults(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> UserDefaultsOut:
    current = await _latest(db, scope="user_default", workspace_id=auth.workspace.id, owner_id=auth.user.id)
    return UserDefaultsOut(version=current.version_no if current else 0, settings=current.settings if current else {})


@router.put("/campaign-defaults", response_model=UserDefaultsOut)
async def save_my_defaults(body: CampaignSettingsSave, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> UserDefaultsOut:
    require_writer(auth)
    settings = await validate_settings(db, body.settings, workspace_id=auth.workspace.id, campaign_kind=None)
    row = await save_version(
        db, scope="user_default", workspace_id=auth.workspace.id, owner_id=auth.user.id, settings=settings,
        reason=body.reason, actor_id=auth.user.id, expected_version=body.expected_version,
    )
    await record_audit(db, action="campaign.defaults_saved", actor_user_id=auth.user.id, workspace_id=auth.workspace.id, subject=str(auth.user.id), detail={"version_no": row.version_no})
    await db.commit()
    return UserDefaultsOut(version=row.version_no, settings=row.settings)


@router.get("/campaign-defaults/versions", response_model=list[CampaignConfigVersionOut])
async def my_default_versions(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> list[CampaignConfigVersionOut]:
    rows = await list_versions(db, scope="user_default", workspace_id=auth.workspace.id, owner_id=auth.user.id)
    return [_version_out(v) for v in rows]


@router.get("/reports/runs/{report_run_id}/location", response_model=ReportLocationOut)
async def locate_report_run(report_run_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> ReportLocationOut:
    """Backward-compatible resolution for historical links (/app/reports?type=..&run=..) that
    carry no campaign. A run resolves only to its own recorded campaign in this workspace."""
    run = (
        await db.execute(select(ReportRun).where(ReportRun.id == report_run_id, ReportRun.workspace_id == auth.workspace.id))
    ).scalar_one_or_none()
    if run is None or run.journey_id is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if run.idempotency_scope == "workspace_legacy":
        mapped = (
            await db.execute(
                select(ReportRunLegacyMapping.journey_id).where(
                    ReportRunLegacyMapping.report_run_id == run.id, ReportRunLegacyMapping.workspace_id == auth.workspace.id
                )
            )
        ).scalar_one_or_none()
        if mapped != run.journey_id:
            raise HTTPException(status_code=404, detail="Report not found")
    await scoped_journey(run.journey_id, db, auth.workspace.id)
    return ReportLocationOut(report_run_id=run.id, journey_id=run.journey_id, report_type=run.report_type)
