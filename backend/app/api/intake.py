"""M4.1 manual property intake API.

POST /api/journeys/{journey_id}/intake           – submit intake
POST /api/journeys/{journey_id}/intake/parse-preview – text-parse preview (no DB writes)
GET  /api/journeys/{journey_id}/intake/{intake_id}   – status read-back
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.db.base import get_db
from app.db.models import IntakeEvent, Property
from app.schemas.intake import IntakeRequest, IntakeResult, ParsedFactsOut
from app.services import parser as text_parser
from app.services.intake import process_intake

router = APIRouter(prefix="/journeys/{journey_id}", tags=["intake"])


@router.post(
    "/intake/parse-preview",
    response_model=ParsedFactsOut,
    summary="Parse pasted listing text without creating any records",
)
async def parse_preview(
    journey_id: uuid.UUID,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> ParsedFactsOut:
    """Parse raw listing text and return extracted facts.  No database writes."""
    # Validate journey ownership (ensures workspace scoping / cross-tenant isolation)
    await scoped_journey(journey_id, db, auth.workspace.id)

    raw_text = body.get("raw_text", "")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="raw_text is required",
        )
    pr = text_parser.parse(raw_text)
    await db.commit()
    return ParsedFactsOut(
        address_line=pr.address_line,
        suburb=pr.suburb,
        state=pr.state,
        postcode=pr.postcode,
        beds=pr.beds,
        baths=pr.baths,
        cars=pr.cars,
        land_sqm=pr.land_sqm,
        floor_sqm=pr.floor_sqm,
        property_type=pr.property_type,
        price_kind=pr.price.price_kind if pr.price else None,
        raw_price=pr.price.raw_price if pr.price else None,
        lower_minor=pr.price.lower_minor if pr.price else None,
        upper_minor=pr.price.upper_minor if pr.price else None,
        review_reasons=pr.review_reasons,
        parser_version=pr.parser_version,
    )


@router.post(
    "/intake",
    response_model=IntakeResult,
    status_code=status.HTTP_200_OK,
    summary="Submit a manual property intake",
)
async def submit_intake(
    journey_id: uuid.UUID,
    body: IntakeRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> IntakeResult:
    """
    Accepts structured, URL-with-facts, or pasted-text payloads.
    Idempotent: replaying the same payload returns the existing result without
    creating duplicate records.
    """
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)

    # Validate mode-payload alignment
    if body.mode == "structured_form" and body.structured is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="structured payload required for mode=structured_form",
        )
    if body.mode == "url_with_facts" and body.url_with_facts is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="url_with_facts payload required for mode=url_with_facts",
        )
    if body.mode == "pasted_text" and body.pasted_text is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pasted_text payload required for mode=pasted_text",
        )

    result = await process_intake(db, journey, auth.user.id, body)
    await db.commit()
    return result


@router.get(
    "/intake/{intake_id}",
    response_model=IntakeResult,
    summary="Get intake event status",
)
async def get_intake(
    journey_id: uuid.UUID,
    intake_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> IntakeResult:
    """Read-back an intake event. Cross-tenant requests return 404."""
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    ev = (
        await db.execute(
            select(IntakeEvent).where(
                IntakeEvent.id == intake_id,
                IntakeEvent.workspace_id == journey.workspace_id,
                IntakeEvent.journey_id == journey.id,
            )
        )
    ).scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake event not found")

    dup_prop: Property | None = None
    if ev.duplicate_property_id is not None:
        dup_prop = (
            await db.execute(
                select(Property).where(Property.id == ev.duplicate_property_id)
            )
        ).scalar_one_or_none()

    await db.commit()
    return IntakeResult(
        intake_id=ev.id,
        state=ev.state,  # type: ignore[arg-type]
        property_id=ev.result_property_id,
        duplicate_property_id=ev.duplicate_property_id,
        duplicate_address=(
            f"{dup_prop.address_line}, {dup_prop.suburb} {dup_prop.state}"
            if dup_prop
            else None
        ),
        review_reasons=ev.review_reasons or [],
        journey_id=ev.journey_id,
    )
