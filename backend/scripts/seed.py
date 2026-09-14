"""Idempotent synthetic seed. Run: `python -m scripts.seed` from /app/backend.

Creates two independent workspaces so cross-tenant isolation can be demonstrated. No live data.
Synthetic sender-alias fixtures are added ONLY to the explicitly-labelled demo/owner workspace.
New real workspaces receive honest empty states.
"""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

from app.core.security import hash_password, now_utc  # noqa: E402
from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import (  # noqa: E402
    BriefVersion,
    ConnectorDefinition,
    ConnectorInstance,
    Journey,
    Membership,
    Property,
    PropertyTask,
    SenderAlias,
    SourceReadiness,
    User,
    Workspace,
)
from app.schemas.brief import Area, BriefPayload, default_brief  # noqa: E402
from app.services.properties import load_demo_properties, reevaluate_journey  # noqa: E402
from app.services.notifications import create_notification_event  # noqa: E402
from app.services.reports import ensure_report_schedule_jobs  # noqa: E402

ACCOUNTS = [
    {
        "email": os.environ.get("SEED_OWNER_EMAIL", "owner@propertyacquisition-demo.com"),
        "password": os.environ.get("SEED_OWNER_PASSWORD", "Prototype2026pass"),
        "display_name": "Nick",
        "workspace": "Brecciaroli household",
        "journey": "Perth family home 2026",
        "is_demo_workspace": True,  # synthetic fixtures seeded here only
    },
    {
        "email": os.environ.get("SEED_DRILL_EMAIL", "lockout-drills@propertyacquisition-demo.com"),
        "password": os.environ.get("SEED_DRILL_PASSWORD", "Prototype2026pass"),
        "display_name": "Lockout drills",
        "workspace": "Lockout drill household",
        "journey": "Drill journey",
        "is_demo_workspace": False,
    },
    {
        "email": os.environ.get("SEED_OTHER_EMAIL", "other@propertyacquisition-demo.com"),
        "password": os.environ.get("SEED_OTHER_PASSWORD", "Prototype2026pass"),
        "display_name": "Other tenant",
        "workspace": "Second household",
        "journey": "Adelaide downsizer",
        "is_demo_workspace": False,
    },
]

# ── Connector catalogue (global, provider-neutral synthetic data) ─────────────
# capabilities: flat list  |  jurisdiction_codes: separate list  |  licence_state: from LICENCE_STATES

CONNECTOR_DEFINITIONS = [
    {
        "slug": "rea-realestate-au",
        "display_name": "REA Group (realestate.com.au)",
        "description": "Major Australian property portal. Synthetic — not connected.",
        "acquisition_mechanism": "portal_api",
        "capabilities": ["listings", "price_history", "agent_profiles"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA", "TAS", "ACT", "NT"],
        "licence_kind": "commercial",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "Data sourced from realestate.com.au (REA Group). Not for redistribution without a commercial licence.",
    },
    {
        "slug": "domain-com-au",
        "display_name": "Domain.com.au",
        "description": "Second-largest Australian property portal. Synthetic — not connected.",
        "acquisition_mechanism": "portal_api",
        "capabilities": ["listings", "price_history", "suburb_profiles"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA", "TAS", "ACT", "NT"],
        "licence_kind": "commercial",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "Data sourced from Domain.com.au. Not for redistribution without a commercial licence.",
    },
    {
        "slug": "corelogic-au",
        "display_name": "CoreLogic Australia",
        "description": "National property analytics platform. Synthetic — not connected.",
        "acquisition_mechanism": "direct_api",
        "capabilities": ["avm", "sales_history", "ownership", "planning"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA", "TAS", "ACT", "NT"],
        "licence_kind": "licensed",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "CoreLogic data is licensed for the buyer's own use only. Redistribution is prohibited without a separate agreement.",
    },
    {
        "slug": "proptrack-rea",
        "display_name": "PropTrack (REA Analytics)",
        "description": "REA Group analytics arm. Synthetic — not connected.",
        "acquisition_mechanism": "direct_api",
        "capabilities": ["avm", "suburb_trends", "price_guidance"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA", "TAS", "ACT", "NT"],
        "licence_kind": "commercial",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "Data sourced from PropTrack (REA Group analytics). Not for redistribution without a commercial licence.",
    },
    {
        "slug": "reiwa-wa",
        "display_name": "REIWA (Real Estate Institute of WA)",
        "description": "WA-specific listing and sales data. Synthetic — not connected.",
        "acquisition_mechanism": "portal_api",
        "capabilities": ["listings", "sales_history", "rental_data"],
        "jurisdiction_codes": ["WA"],
        "licence_kind": "licensed",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "REIWA member data is licensed for the buyer's own use only. Redistribution requires REIWA member access.",
    },
    {
        "slug": "reiq-qld",
        "display_name": "REIQ (Real Estate Institute of QLD)",
        "description": "QLD-specific listing and market reports. Synthetic — not connected.",
        "acquisition_mechanism": "portal_api",
        "capabilities": ["listings", "market_reports"],
        "jurisdiction_codes": ["QLD"],
        "licence_kind": "licensed",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "REIQ member data is licensed for the buyer's own use only. Redistribution requires REIQ member access.",
    },
    {
        "slug": "reiv-vic",
        "display_name": "REIV (Real Estate Institute of VIC)",
        "description": "VIC auction clearance and listing data. Synthetic — not connected.",
        "acquisition_mechanism": "portal_api",
        "capabilities": ["listings", "clearance_rates"],
        "jurisdiction_codes": ["VIC"],
        "licence_kind": "licensed",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "REIV member data is licensed for the buyer's own use only. Redistribution requires REIV member access.",
    },
    {
        "slug": "pricefinder-au",
        "display_name": "PriceFinder",
        "description": "Property analytics and AVM service. Synthetic — not connected.",
        "acquisition_mechanism": "direct_api",
        "capabilities": ["sales_history", "avm", "suburb_analytics"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA"],
        "licence_kind": "commercial",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "PriceFinder data is licensed for the buyer's own use only. Not for redistribution without a commercial licence.",
    },
    {
        "slug": "email-inbound",
        "display_name": "Email Forwarding (Inbound)",
        "description": "Inbound email alias for listing alerts. No mailbox connected.",
        "acquisition_mechanism": "inbound_email",
        "capabilities": ["listing_alerts", "agent_correspondence"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA", "TAS", "ACT", "NT"],
        "licence_kind": "none_required",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": True,
        "attribution_text": None,
    },
    {
        "slug": "onthehouse-au",
        "display_name": "OnTheHouse (REA subsidiary)",
        "description": "Listed and sold price data. Synthetic — not connected.",
        "acquisition_mechanism": "portal_scrape",
        "capabilities": ["listings", "sold_prices"],
        "jurisdiction_codes": ["WA", "NSW", "VIC", "QLD", "SA"],
        "licence_kind": "commercial",
        "licence_state": "not_required",
        "version": "synthetic-1.0",
        "redistribution_allowed": False,
        "attribution_text": "Data sourced from OnTheHouse (REA Group subsidiary). Not for redistribution — scraped source terms apply.",
    },
]

# ── Demo workspace connector instances (synthetic states for sources screen) ──
# Seeded ONLY into the demo/owner workspace. New real workspaces start empty.

DEMO_CONNECTOR_INSTANCES = [
    {
        "slug": "email-inbound",
        "enabled": True,
        "readiness_state": "unconfigured",
        "health_detail": "No email alias configured yet — setup required",
        "source_readiness": {
            "readiness_state": "offline",
            "requested_filters": {"jurisdictions": ["WA"], "keywords": ["listing alert", "price drop"]},
            "effective_filters": {},
            "deviation_reason": "No active mailbox — unable to apply requested jurisdiction or keyword filters",
        },
    },
    {
        "slug": "rea-realestate-au",
        "enabled": False,
        "readiness_state": "unconfigured",
        "health_detail": "API credentials not configured. Contact REA Group for commercial access.",
        "source_readiness": None,
    },
    {
        "slug": "reiwa-wa",
        "enabled": True,
        "readiness_state": "unconfigured",
        "health_detail": "Licensed API key required — contact REIWA for member access.",
        "source_readiness": {
            "readiness_state": "offline",
            "requested_filters": {"jurisdictions": ["WA"], "property_types": ["house", "townhouse"]},
            "effective_filters": {},
            "deviation_reason": "API key absent — no data can be retrieved until licence is active",
        },
    },
]

# ── Synthetic sender-alias fixtures for demo workspace only ──────────────────
# display_names_seen is a list stored for reference; never used as a matching key.

DEMO_ALIAS_FIXTURES = [
    {
        "canonical_email": "nick@brecciaroli.com.au",
        "alias_email": "nick.brecciaroli@realestate.com.au",
        "display_names_seen": ["Nick Brecciaroli (REA notifications)"],
        "evidence_label": "Synthetic: confirmed sender match via display name",
        "evidence_url": None,
        "confidence": "high",
        "review_state": "confirmed",
    },
    {
        "canonical_email": "nick@brecciaroli.com.au",
        "alias_email": "swanvalley.alerts@realestate.com.au",
        "display_names_seen": ["Swan Valley Alerts"],
        "evidence_label": "Synthetic: display name does not identify the recipient",
        "evidence_url": None,
        "confidence": "medium",
        "review_state": "pending",
    },
    {
        "canonical_email": "nick@brecciaroli.com.au",
        "alias_email": "crest.property.perth@gmail.com",
        "display_names_seen": ["Crest Property Perth"],
        "evidence_label": "Synthetic: email domain does not match canonical",
        "evidence_url": None,
        "confidence": "low",
        "review_state": "pending",
    },
    {
        "canonical_email": "nick@brecciaroli.com.au",
        "alias_email": "info@crestproperty.com.au",
        "display_names_seen": ["Crest Property Info"],
        "evidence_label": "Synthetic: confirmed generic agency inbox — unrelated to buyer",
        "evidence_url": None,
        "confidence": "low",
        "review_state": "rejected",
    },
]


async def _seed_connectors(db: AsyncSession) -> None:
    """Seed global connector definitions idempotently.
    Also removes any stale rows whose slugs don't match the known catalogue."""
    known_slugs = {defn["slug"] for defn in CONNECTOR_DEFINITIONS}
    # Purge any orphan rows created by earlier broken seed runs
    all_existing = (await db.execute(select(ConnectorDefinition))).scalars().all()
    for row in all_existing:
        if row.slug not in known_slugs:
            await db.delete(row)
    await db.flush()

    for defn in CONNECTOR_DEFINITIONS:
        existing = (
            await db.execute(
                select(ConnectorDefinition).where(ConnectorDefinition.slug == defn["slug"])
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                ConnectorDefinition(
                    slug=defn["slug"],
                    display_name=defn["display_name"],
                    acquisition_mechanism=defn["acquisition_mechanism"],
                    licence_kind=defn["licence_kind"],
                    licence_state=defn["licence_state"],
                    version=defn["version"],
                    kill_switch=False,
                    capabilities=defn["capabilities"],
                    jurisdiction_codes=defn["jurisdiction_codes"],
                    description=defn.get("description"),
                    redistribution_allowed=defn.get("redistribution_allowed", False),
                    attribution_text=defn.get("attribution_text"),
                )
            )
        else:
            existing.redistribution_allowed = defn.get("redistribution_allowed", False)
            existing.attribution_text = defn.get("attribution_text")
    await db.flush()


async def _seed_demo_aliases(db: AsyncSession, workspace_id: object) -> None:
    """Add synthetic sender-alias fixtures ONLY to the demo workspace."""
    for fixture in DEMO_ALIAS_FIXTURES:
        existing = (
            await db.execute(
                select(SenderAlias).where(
                    SenderAlias.workspace_id == workspace_id,
                    SenderAlias.alias_email == fixture["alias_email"],
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                SenderAlias(
                    workspace_id=workspace_id,
                    canonical_email=fixture["canonical_email"],
                    alias_email=fixture["alias_email"],
                    display_names_seen=fixture["display_names_seen"],
                    evidence_label=fixture["evidence_label"],
                    evidence_url=fixture.get("evidence_url"),
                    confidence=fixture["confidence"],
                    review_state=fixture["review_state"],
                    first_seen_at=now_utc(),
                )
            )
    await db.flush()


async def _seed_demo_instances(db: AsyncSession, workspace_id: object, actor_id: object) -> None:
    """Seed ConnectorInstance + SourceReadiness for the demo workspace only."""
    for spec in DEMO_CONNECTOR_INSTANCES:
        defn = (
            await db.execute(
                select(ConnectorDefinition).where(ConnectorDefinition.slug == spec["slug"])
            )
        ).scalar_one_or_none()
        if defn is None:
            continue

        ci = (
            await db.execute(
                select(ConnectorInstance).where(
                    ConnectorInstance.workspace_id == workspace_id,
                    ConnectorInstance.definition_id == defn.id,
                )
            )
        ).scalar_one_or_none()

        if ci is None:
            ci = ConnectorInstance(
                workspace_id=workspace_id,
                definition_id=defn.id,
                enabled=spec["enabled"],
                readiness_state=spec["readiness_state"],
                health_detail=spec.get("health_detail"),
                consent_actor_user_id=actor_id if spec["enabled"] else None,
                consent_given_at=now_utc() if spec["enabled"] else None,
            )
            db.add(ci)
            await db.flush()

        sr_spec = spec.get("source_readiness")
        if sr_spec:
            sr = (
                await db.execute(
                    select(SourceReadiness).where(
                        SourceReadiness.workspace_id == workspace_id,
                        SourceReadiness.connector_instance_id == ci.id,
                    )
                )
            ).scalar_one_or_none()
            if sr is None:
                db.add(
                    SourceReadiness(
                        workspace_id=workspace_id,
                        connector_instance_id=ci.id,
                        readiness_state=sr_spec["readiness_state"],
                        requested_filters=sr_spec["requested_filters"],
                        effective_filters=sr_spec["effective_filters"],
                        deviation_reason=sr_spec.get("deviation_reason"),
                    )
                )
                await db.flush()


async def _seed_demo_notifications(db: AsyncSession, workspace_id: object, journey: Journey, user: User) -> None:
    """Create M5.1 examples only for the explicitly labelled demo workspace."""
    property_row = (
        await db.execute(select(Property).where(Property.workspace_id == workspace_id).order_by(Property.created_at))
    ).scalars().first()
    if property_row is None:
        return
    task = (
        await db.execute(
            select(PropertyTask).where(PropertyTask.workspace_id == workspace_id, PropertyTask.title == "Review the contract conditions")
        )
    ).scalar_one_or_none()
    if task is None:
        task = PropertyTask(
            workspace_id=workspace_id,
            journey_id=journey.id,
            property_id=property_row.id,
            title="Review the contract conditions",
            notes="Synthetic example for the demo workspace only.",
            assignee_user_id=user.id,
            priority="high",
            due_at=now_utc(),
            timezone="Australia/Perth",
            reminder_offset_minutes=60,
            status="open",
            created_by=user.id,
        )
        db.add(task)
        await db.flush()
    await create_notification_event(
        db,
        workspace_id=workspace_id,
        category="evidence_gap",
        fingerprint="demo:m5-1:evidence-gap",
        title="Evidence gap to review",
        message="Synthetic example: confirm the land-size evidence for this property.",
        safe_deep_link=f"/app/properties/{property_row.id}",
        priority="high",
        property_id=property_row.id,
        evidence_ref={"synthetic": True},
    )
    await create_notification_event(
        db,
        workspace_id=workspace_id,
        category="task_due_soon",
        fingerprint="demo:m5-1:task-due-soon",
        title=f"Task due soon: {task.title}",
        message="Synthetic example: this task needs attention.",
        safe_deep_link=f"/app/tasks?task={task.id}",
        priority="high",
        property_id=property_row.id,
        task_id=task.id,
        recipient_ids={user.id},
        evidence_ref={"synthetic": True},
    )


def _seed_brief() -> BriefPayload:
    """Aligned with fixtures/demo-data.json: ceiling $1.3m, detached house, 3 beds, 1 bath, 400 m² land."""
    brief = default_brief()
    brief.budget.ceiling_minor = 1_300_000_00
    brief.budget.preferred_max_minor = 1_200_000_00
    brief.property_profile.types_mode = "hard"
    brief.property_profile.types = ["house"]
    brief.property_profile.detached_mode = "hard"
    brief.property_profile.detached_required = True
    brief.beds.mode = "hard"
    brief.beds.min = 3
    brief.baths.mode = "hard"
    brief.baths.min = 1
    brief.parking.min = 2
    brief.land_sqm.min = 400
    brief.renovation.level = "moderate"
    brief.timing.horizon = "6_months"
    brief.locations.states = ["WA"]
    brief.locations.included = [
        Area(suburb="Example Park", state="WA", postcode=None),
        Area(suburb="Example North", state="WA", postcode=None),
        Area(suburb="Example Coast", state="WA", postcode=None),
        Area(suburb="Example Central", state="WA", postcode=None),
    ]
    return BriefPayload.model_validate(brief.model_dump())


async def _seed_account(db: AsyncSession, spec: dict) -> None:
    email = spec["email"].lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(spec["password"]),
            display_name=spec["display_name"],
            email_verified_at=now_utc(),
        )
        db.add(user)
        await db.flush()
    else:
        user.password_hash = hash_password(spec["password"])
        user.email_verified_at = user.email_verified_at or now_utc()

    workspace = (
        await db.execute(select(Workspace).where(Workspace.owner_user_id == user.id))
    ).scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(name=spec["workspace"], owner_user_id=user.id)
        db.add(workspace)
        await db.flush()
        db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await ensure_report_schedule_jobs(db, workspace.id)

    journey = (
        await db.execute(select(Journey).where(Journey.workspace_id == workspace.id))
    ).scalar_one_or_none()
    if journey is None:
        brief = _seed_brief()
        journey = Journey(
            workspace_id=workspace.id,
            name=spec["journey"],
            status="active",
            onboarding_step=6,
            onboarding_completed_at=now_utc(),
            draft_payload=brief.model_dump(),
            created_by=user.id,
        )
        db.add(journey)
        await db.flush()
        version = BriefVersion(
            workspace_id=workspace.id,
            journey_id=journey.id,
            version_no=1,
            payload=brief.model_dump(),
            reason="Seeded synthetic brief",
            actor_user_id=user.id,
        )
        db.add(version)
        await db.flush()
        journey.current_version_id = version.id
    else:
        current = (
            await db.execute(select(BriefVersion).where(BriefVersion.id == journey.current_version_id))
        ).scalar_one_or_none()
        target = _seed_brief().model_dump()
        if current is None or current.payload != target:
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
                workspace_id=workspace.id,
                journey_id=journey.id,
                version_no=next_no,
                payload=target,
                reason="Seed realigned to fixtures/demo-data.json (Milestone 3)",
                actor_user_id=user.id,
            )
            db.add(version)
            await db.flush()
            journey.current_version_id = version.id
            journey.draft_payload = target
            journey.row_version += 1
    await db.flush()
    created = await load_demo_properties(db, journey, user.id)
    version = (
        await db.execute(select(BriefVersion).where(BriefVersion.id == journey.current_version_id))
    ).scalar_one()
    queued = (
        (
            await db.execute(
                select(BriefVersion).where(
                    BriefVersion.journey_id == journey.id,
                    BriefVersion.reevaluation_state == "queued",
                    BriefVersion.id != version.id,
                )
            )
        )
        .scalars()
        .all()
    )
    for old in queued:
        await reevaluate_journey(db, journey, old, user.id)
    evaluated = await reevaluate_journey(db, journey, version, user.id)
    if spec.get("is_demo_workspace"):
        await _seed_demo_aliases(db, workspace.id)
        await _seed_demo_instances(db, workspace.id, user.id)
        await _seed_demo_notifications(db, workspace.id, journey, user)
    print(
        f"seeded {email} · workspace {workspace.name} · journey {journey.name} · "
        f"{created} fixture properties added · {evaluated} evaluated against brief v{version.version_no}"
    )


async def main() -> None:
    env = os.environ.get("APP_ENV", "development").strip().lower()
    if env == "production":
        print(
            "ERROR: seed.py must not run in production (APP_ENV=production). "
            "Use scripts/bootstrap_owner.py to provision the owner account."
        )
        return
    async with get_sessionmaker()() as db:
        await _seed_connectors(db)
        for spec in ACCOUNTS:
            await _seed_account(db, spec)
        await db.commit()
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
