import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import BriefVersion, Journey, User
from app.schemas.brief import (
    DEFAULT_WEIGHTS,
    BriefPayload,
    default_brief,
    enabled_weight_total,
    validate_for_publish,
)
from app.schemas.journeys import (
    BriefOut,
    BriefVersionOut,
    DraftSave,
    JourneyCreate,
    JourneyOut,
    JourneyUpdate,
    PublishRequest,
)

router = APIRouter(prefix="/journeys", tags=["journeys"])


async def _published_count(db: AsyncSession, journey: Journey) -> int:
    return int(
        (
            await db.execute(
                select(func.count()).select_from(BriefVersion).where(BriefVersion.journey_id == journey.id)
            )
        ).scalar_one()
    )


async def _current_version(db: AsyncSession, journey: Journey) -> BriefVersion | None:
    if journey.current_version_id is None:
        return None
    return (
        await db.execute(select(BriefVersion).where(BriefVersion.id == journey.current_version_id))
    ).scalar_one_or_none()


async def _journey_out(db: AsyncSession, journey: Journey) -> JourneyOut:
    current = await _current_version(db, journey)
    return JourneyOut(
        id=journey.id,
        name=journey.name,
        status=journey.status,
        timezone=journey.timezone,
        onboarding_step=journey.onboarding_step,
        onboarding_complete=journey.onboarding_completed_at is not None,
        row_version=journey.row_version,
        current_version_no=current.version_no if current else None,
        published_versions=await _published_count(db, journey),
        created_at=journey.created_at,
        updated_at=journey.updated_at,
    )


async def _version_out(db: AsyncSession, version: BriefVersion) -> BriefVersionOut:
    email = (await db.execute(select(User.email).where(User.id == version.actor_user_id))).scalar_one()
    return BriefVersionOut(
        id=version.id,
        version_no=version.version_no,
        reason=version.reason,
        published_at=version.published_at,
        actor_email=email,
        reevaluation_state=version.reevaluation_state,
        payload=BriefPayload.model_validate(version.payload),
    )


def _check_row_version(journey: Journey, expected: int) -> None:
    if journey.row_version != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This journey changed in another session. Reload before saving again.",
        )


@router.get("", response_model=list[JourneyOut])
async def list_journeys(
    auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> list[JourneyOut]:
    rows = (
        await db.execute(
            select(Journey).where(Journey.workspace_id == auth.workspace.id).order_by(Journey.created_at)
        )
    ).scalars()
    return [await _journey_out(db, j) for j in rows]


@router.post("", response_model=JourneyOut, status_code=status.HTTP_201_CREATED)
async def create_journey(
    body: JourneyCreate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> JourneyOut:
    require_writer(auth)
    journey = Journey(
        workspace_id=auth.workspace.id,
        name=body.name.strip(),
        timezone=body.timezone,
        draft_payload=default_brief().model_dump(),
        created_by=auth.user.id,
    )
    db.add(journey)
    await db.commit()
    return await _journey_out(db, journey)


@router.get("/{journey_id}", response_model=JourneyOut)
async def get_journey(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> JourneyOut:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    return await _journey_out(db, journey)


@router.patch("/{journey_id}", response_model=JourneyOut)
async def update_journey(
    journey_id: uuid.UUID,
    body: JourneyUpdate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> JourneyOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    _check_row_version(journey, body.expected_row_version)
    if body.name is not None:
        journey.name = body.name.strip()
    if body.timezone is not None:
        journey.timezone = body.timezone
    if body.onboarding_step is not None:
        journey.onboarding_step = body.onboarding_step
    if body.status is not None:
        journey.status = body.status
    journey.row_version += 1
    await db.commit()
    await db.refresh(journey)
    return await _journey_out(db, journey)


@router.post("/{journey_id}/complete-onboarding", response_model=JourneyOut)
async def complete_onboarding(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> JourneyOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    if journey.onboarding_completed_at is None:
        journey.onboarding_completed_at = now_utc()
    journey.status = "active" if journey.status == "onboarding" else journey.status
    journey.onboarding_step = 6
    journey.row_version += 1
    await db.commit()
    await db.refresh(journey)
    return await _journey_out(db, journey)


@router.get("/{journey_id}/brief", response_model=BriefOut)
async def get_brief(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> BriefOut:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    draft = BriefPayload.model_validate(journey.draft_payload)
    current = await _current_version(db, journey)
    return BriefOut(
        journey=await _journey_out(db, journey),
        draft=draft,
        draft_updated_at=journey.draft_updated_at,
        validation=validate_for_publish(draft),
        current_version=await _version_out(db, current) if current else None,
        weight_total_enabled=enabled_weight_total(draft.weights),
    )


@router.put("/{journey_id}/brief/draft", response_model=BriefOut)
async def save_draft(
    journey_id: uuid.UUID,
    body: DraftSave,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> BriefOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    _check_row_version(journey, body.expected_row_version)
    journey.draft_payload = body.payload.model_dump()
    journey.draft_updated_at = now_utc()
    if body.onboarding_step is not None:
        journey.onboarding_step = body.onboarding_step
    journey.row_version += 1
    await db.commit()
    await db.refresh(journey)
    return await get_brief(journey_id, auth, db)


@router.post("/{journey_id}/brief/reset-weights", response_model=BriefOut)
async def reset_weights(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> BriefOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    draft = BriefPayload.model_validate(journey.draft_payload)
    draft.weights = DEFAULT_WEIGHTS.model_copy()
    journey.draft_payload = draft.model_dump()
    journey.draft_updated_at = now_utc()
    journey.row_version += 1
    await db.commit()
    await db.refresh(journey)
    return await get_brief(journey_id, auth, db)


@router.post("/{journey_id}/brief/publish", response_model=BriefOut, status_code=status.HTTP_201_CREATED)
async def publish_brief(
    journey_id: uuid.UUID,
    body: PublishRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> BriefOut:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    _check_row_version(journey, body.expected_row_version)
    draft = BriefPayload.model_validate(journey.draft_payload)

    errors = validate_for_publish(draft)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "brief_invalid",
                "message": "Fix the highlighted fields before publishing.",
                "errors": [e.model_dump() for e in errors],
            },
        )

    next_no = (
        int(
            (
                await db.execute(
                    select(func.coalesce(func.max(BriefVersion.version_no), 0)).where(
                        BriefVersion.journey_id == journey.id
                    )
                )
            ).scalar_one()
        )
        + 1
    )
    version = BriefVersion(
        workspace_id=auth.workspace.id,
        journey_id=journey.id,
        version_no=next_no,
        payload=draft.model_dump(),
        reason=body.reason.strip(),
        actor_user_id=auth.user.id,
        reevaluation_state="queued",
    )
    db.add(version)
    await db.flush()
    journey.current_version_id = version.id
    if journey.status == "onboarding":
        journey.status = "active"
    journey.row_version += 1
    await db.commit()
    await db.refresh(journey)
    return await get_brief(journey_id, auth, db)


@router.get("/{journey_id}/brief/versions", response_model=list[BriefVersionOut])
async def list_versions(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> list[BriefVersionOut]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    rows = (
        await db.execute(
            select(BriefVersion)
            .where(BriefVersion.journey_id == journey.id)
            .order_by(BriefVersion.version_no.desc())
        )
    ).scalars()
    return [await _version_out(db, v) for v in rows]
