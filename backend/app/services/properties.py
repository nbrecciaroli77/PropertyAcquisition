"""Property workspace services: fixture loading, evaluation persistence, workflow transitions."""

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import (
    ActivityEvent,
    BriefVersion,
    BuyerProperty,
    Fact,
    GateWaiver,
    Journey,
    ListingCampaign,
    MatchEvaluation,
    Observation,
    Property,
)
from app.schemas.brief import BriefPayload
from app.services.matching import EVALUATION_VERSION, FactValue, PriceInput, PropertyInput, evaluate

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "demo-data.json"

PRICE_KIND_MAP = {
    "Exact": "exact",
    "Range": "range",
    "From": "from",
    "Offers over": "offers_over",
    "Auction": "auction",
    "Contact agent": "contact_agent",
    "Expressions of interest": "expressions_of_interest",
    "Conflicting": "conflicting",
}
MARKET_MAP = {"Active": "active", "Under offer": "under_offer", "Withdrawn": "withdrawn", "Sold": "sold"}
BUYER_MAP = {
    "Reviewing": "reviewing",
    "Shortlisted": "shortlisted",
    "Inspection considered": "inspection_considered",
    "Inspected": "inspected",
    "Due diligence": "due_diligence",
    "Offer preparation": "offer_preparation",
    "Offer submitted": "offer_submitted",
    "Under contract": "under_contract",
    "Settled": "settled",
    "Rejected": "rejected",
    "Archived": "archived",
}
CONDITION_MAP = {"Usable home": "usable_home", "Renovation": "renovation", "Move-in ready": "move_in_ready"}
TIER_MAP = {"Primary": "primary", "Strong alternative": "strong_alternative", "Conditional": "conditional"}
SOURCE_MAP = {
    "original-source": ("original_source", "Original listing (synthetic)"),
    "partial": ("partial", "Partial listing (synthetic)"),
    "conflict": ("conflict", "Two sources in conflict (synthetic)"),
    "manual": ("manual", "Manual entry"),
}
# Deterministic freshness offsets so seeded evidence shows fresh, ageing and stale bands.
CHECKED_DAYS_AGO = {
    "DEMO-001": 0,
    "DEMO-002": 1,
    "DEMO-003": 2,
    "DEMO-004": 0,
    "DEMO-005": 3,
    "DEMO-006": 3,
    "DEMO-007": 6,
}

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "reviewing": ("shortlisted", "rejected", "archived"),
    "shortlisted": ("inspection_considered", "reviewing", "rejected", "archived"),
    "inspection_considered": ("inspected", "shortlisted", "rejected", "archived"),
    "inspected": ("due_diligence", "shortlisted", "rejected", "archived"),
    "due_diligence": ("offer_preparation", "inspected", "rejected", "archived"),
    "offer_preparation": ("offer_submitted", "due_diligence", "rejected", "archived"),
    "offer_submitted": ("under_contract", "offer_preparation", "rejected", "archived"),
    "under_contract": ("settled", "offer_submitted", "archived"),
    "settled": ("archived",),
    "rejected": ("reviewing", "archived"),
    "archived": ("reviewing",),
}
FORWARD_STATES = (
    "shortlisted",
    "inspection_considered",
    "inspected",
    "due_diligence",
    "offer_preparation",
    "offer_submitted",
    "under_contract",
    "settled",
)

_UNIT_RE = re.compile(r"^(\d+)([A-Za-z])\b")


def normalise_address(address_line: str, suburb: str, state: str) -> tuple[str, str | None]:
    """Keeps the unit suffix in the key so 81A and 81C never collide."""
    line = re.sub(r"\s+", " ", address_line.strip())
    m = _UNIT_RE.match(line)
    unit = m.group(2).upper() if m else None
    key = f"{line.lower()}|{suburb.strip().lower()}|{state.upper()}"
    return key, unit


def _int_fact(ws: uuid.UUID, prop_id: uuid.UUID, obs_id: uuid.UUID, key: str, v: int | None) -> Fact:
    return Fact(
        workspace_id=ws,
        property_id=prop_id,
        observation_id=obs_id,
        key=key,
        value_state="known" if v is not None else "unknown",
        value_int=v,
    )


def load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open() as fh:
        data: dict[str, Any] = json.load(fh)
    return data


async def load_demo_properties(db: AsyncSession, journey: Journey, actor_id: uuid.UUID) -> int:
    """Idempotent: a fixture property already present in the workspace is left untouched."""
    fixture = load_fixture()
    now = now_utc()
    created = 0
    for raw in fixture["properties"]:
        key, unit = normalise_address(raw["address"], raw["suburb"], raw["state"])
        exists = (
            await db.execute(
                select(Property.id).where(
                    Property.workspace_id == journey.workspace_id, Property.normalised_address == key
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue
        prop = Property(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            legacy_ref=raw["legacyRef"],
            address_line=raw["address"],
            unit=unit,
            suburb=raw["suburb"],
            state=raw["state"],
            normalised_address=key,
            synthetic=True,
            created_by=actor_id,
        )
        db.add(prop)
        await db.flush()
        source_kind, source_label = SOURCE_MAP[raw["evidence"]]
        checked = now - timedelta(days=CHECKED_DAYS_AGO.get(raw["legacyRef"], 0))
        obs = Observation(
            workspace_id=journey.workspace_id,
            property_id=prop.id,
            source_kind=source_kind,
            source_label=source_label,
            observed_at=checked - timedelta(hours=2),
            checked_at=checked,
            note=("Index and detail pages disagree on the guide." if raw["evidence"] == "conflict" else None),
        )
        db.add(obs)
        await db.flush()
        db.add(
            ListingCampaign(
                workspace_id=journey.workspace_id,
                property_id=prop.id,
                source_label=source_label,
                market_state=MARKET_MAP.get(raw["marketState"], "unknown"),
                price_kind=PRICE_KIND_MAP[raw["priceKind"]],
                raw_price=raw["rawPrice"],
                lower_minor=raw["lowerPrice"] * 100 if raw.get("lowerPrice") is not None else None,
                upper_minor=raw["upperPrice"] * 100 if raw.get("upperPrice") is not None else None,
                price_source=source_label,
                last_checked_at=checked,
            )
        )
        facts: list[Fact] = []

        for key, fixture_key in (
            ("beds", "beds"),
            ("baths", "baths"),
            ("cars", "cars"),
            ("land_sqm", "landSqm"),
        ):
            facts.append(_int_fact(journey.workspace_id, prop.id, obs.id, key, raw.get(fixture_key)))
        facts.append(
            Fact(
                workspace_id=journey.workspace_id,
                property_id=prop.id,
                observation_id=obs.id,
                key="floor_sqm",
                value_state="unknown",
            )
        )
        facts.append(
            Fact(
                workspace_id=journey.workspace_id,
                property_id=prop.id,
                observation_id=obs.id,
                key="property_type",
                value_state="known",
                value_text="house",
            )
        )
        facts.append(
            Fact(
                workspace_id=journey.workspace_id,
                property_id=prop.id,
                observation_id=obs.id,
                key="detached",
                value_state="known",
                value_bool=True,
            )
        )
        cond = CONDITION_MAP.get(raw.get("condition") or "")
        facts.append(
            Fact(
                workspace_id=journey.workspace_id,
                property_id=prop.id,
                observation_id=obs.id,
                key="condition",
                value_state="known" if cond else "unknown",
                value_text=cond,
            )
        )
        tier = TIER_MAP.get(raw.get("locationTier") or "")
        facts.append(
            Fact(
                workspace_id=journey.workspace_id,
                property_id=prop.id,
                observation_id=obs.id,
                key="location_tier",
                value_state="known" if tier else "unknown",
                value_text=tier,
            )
        )
        db.add_all(facts)
        db.add(
            BuyerProperty(
                workspace_id=journey.workspace_id,
                journey_id=journey.id,
                property_id=prop.id,
                buyer_state=BUYER_MAP[raw["buyerState"]],
                saved=raw["buyerState"] == "Shortlisted",
            )
        )
        db.add(
            ActivityEvent(
                workspace_id=journey.workspace_id,
                journey_id=journey.id,
                property_id=prop.id,
                kind="property_added",
                summary=f"Synthetic fixture {raw['legacyRef']} loaded",
                detail={"source": "fixtures/demo-data.json"},
                actor_user_id=actor_id,
            )
        )
        created += 1
    await db.flush()
    return created


async def build_input(db: AsyncSession, prop: Property) -> PropertyInput:
    campaign = (
        await db.execute(
            select(ListingCampaign)
            .where(ListingCampaign.property_id == prop.id, ListingCampaign.is_current.is_(True))
            .order_by(ListingCampaign.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    price = (
        PriceInput(
            campaign.price_kind,
            campaign.raw_price,
            campaign.lower_minor,
            campaign.upper_minor,
            campaign.price_source,
        )
        if campaign
        else PriceInput("contact_agent", "No campaign", None, None, "None")
    )
    rows = (
        await db.execute(
            select(Fact, Observation.source_label)
            .join(Observation, Observation.id == Fact.observation_id)
            .where(Fact.property_id == prop.id)
        )
    ).all()
    facts = {
        f.key: FactValue(f.value_state, f.value_int, f.value_text, f.value_bool, label, f.conflict_note)
        for f, label in rows
    }
    return PropertyInput(prop.suburb, prop.state, price, facts)


async def evaluate_property(db: AsyncSession, prop: Property, version: BriefVersion) -> MatchEvaluation:
    """Deterministic: same brief version + same facts produce the same stored result."""
    brief = BriefPayload.model_validate(version.payload)
    result = evaluate(brief, await build_input(db, prop), version.version_no)
    existing = (
        await db.execute(
            select(MatchEvaluation).where(
                MatchEvaluation.property_id == prop.id, MatchEvaluation.brief_version_id == version.id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = MatchEvaluation(
            workspace_id=prop.workspace_id,
            journey_id=prop.journey_id,
            property_id=prop.id,
            brief_version_id=version.id,
            evaluation_version=EVALUATION_VERSION,
            input_hash=result["input_hash"],
            verdict=result["verdict"],
            fit_pct=result["fit"]["pct"],
            coverage_pct=result["coverage"]["pct"] or 0,
            result=result,
        )
        db.add(existing)
    elif existing.input_hash != result["input_hash"]:
        existing.input_hash = result["input_hash"]
        existing.verdict = result["verdict"]
        existing.fit_pct = result["fit"]["pct"]
        existing.coverage_pct = result["coverage"]["pct"] or 0
        existing.result = result
        existing.computed_at = now_utc()
    await db.flush()
    return existing


async def reevaluate_journey(
    db: AsyncSession, journey: Journey, version: BriefVersion, actor_id: uuid.UUID | None
) -> int:
    props = (await db.execute(select(Property).where(Property.journey_id == journey.id))).scalars().all()
    for prop in props:
        await evaluate_property(db, prop, version)
    version.reevaluation_state = "completed"
    db.add(
        ActivityEvent(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            kind="reevaluation",
            summary=f"Re-evaluated {len(props)} properties against brief version {version.version_no}",
            detail={"brief_version_no": version.version_no, "evaluation_version": EVALUATION_VERSION},
            actor_user_id=actor_id,
        )
    )
    await db.flush()
    return len(props)


async def current_evaluation(db: AsyncSession, prop: Property, journey: Journey) -> MatchEvaluation | None:
    if journey.current_version_id is None:
        return None
    ev = (
        await db.execute(
            select(MatchEvaluation).where(
                MatchEvaluation.property_id == prop.id,
                MatchEvaluation.brief_version_id == journey.current_version_id,
            )
        )
    ).scalar_one_or_none()
    if ev is None:
        version = (
            await db.execute(select(BriefVersion).where(BriefVersion.id == journey.current_version_id))
        ).scalar_one()
        ev = await evaluate_property(db, prop, version)
    return ev


async def active_waivers(db: AsyncSession, prop: Property, journey: Journey) -> list[GateWaiver]:
    return list(
        (
            await db.execute(
                select(GateWaiver)
                .where(
                    GateWaiver.property_id == prop.id,
                    GateWaiver.journey_id == journey.id,
                    GateWaiver.revoked_at.is_(None),
                )
                .order_by(GateWaiver.created_at)
            )
        )
        .scalars()
        .all()
    )


def check_transition(
    bp: BuyerProperty, to_state: str, evaluation: MatchEvaluation | None, waived: set[str]
) -> None:
    if to_state not in ALLOWED_TRANSITIONS.get(bp.buyer_state, ()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "transition_not_allowed",
                "message": (
                    f"Cannot move from {bp.buyer_state.replace('_', ' ')} to {to_state.replace('_', ' ')}."
                ),
            },
        )
    if to_state in FORWARD_STATES and evaluation is not None and evaluation.verdict == "fail":
        failing = {g["criterion"] for g in evaluation.result["gates"] if g["outcome"] == "fail"}
        if not failing.issubset(waived):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "hard_failure_cannot_be_promoted",
                    "message": (
                        "A known hard-rule failure cannot be promoted. Record a reasoned waiver for each "
                        "failing rule first; the gate will still show Fail."
                    ),
                    "failing": sorted(failing - waived),
                },
            )


def check_row_version(actual: int, expected: int, what: str) -> None:
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "stale_write",
                "message": f"This {what} changed in another session. Reload before saving again.",
            },
        )


def freshness_band(checked_at: datetime) -> str:
    age = now_utc() - checked_at
    if age <= timedelta(days=2):
        return "fresh"
    if age <= timedelta(days=5):
        return "ageing"
    return "stale"
