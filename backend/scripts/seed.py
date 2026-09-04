"""Idempotent synthetic seed. Run: `python -m scripts.seed` from /app/backend.

Creates two independent workspaces so cross-tenant isolation can be demonstrated. No live data.
"""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

from app.core.security import hash_password, now_utc  # noqa: E402
from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import BriefVersion, Journey, Membership, User, Workspace  # noqa: E402
from app.schemas.brief import Area, BriefPayload, default_brief  # noqa: E402
from app.services.properties import load_demo_properties, reevaluate_journey  # noqa: E402

ACCOUNTS = [
    {
        "email": os.environ.get("SEED_OWNER_EMAIL", "owner@propertyacquisition-demo.com"),
        "password": os.environ.get("SEED_OWNER_PASSWORD", "Prototype2026pass"),
        "display_name": "Nick",
        "workspace": "Brecciaroli household",
        "journey": "Perth family home 2026",
    },
    {
        # Used only for brute-force drills so the owner account is never locked out mid-demo.
        "email": os.environ.get("SEED_DRILL_EMAIL", "lockout-drills@propertyacquisition-demo.com"),
        "password": os.environ.get("SEED_DRILL_PASSWORD", "Prototype2026pass"),
        "display_name": "Lockout drills",
        "workspace": "Lockout drill household",
        "journey": "Drill journey",
    },
    {
        "email": os.environ.get("SEED_OTHER_EMAIL", "other@propertyacquisition-demo.com"),
        "password": os.environ.get("SEED_OTHER_PASSWORD", "Prototype2026pass"),
        "display_name": "Other tenant",
        "workspace": "Second household",
        "journey": "Adelaide downsizer",
    },
]


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


async def _seed_account(db: AsyncSession, spec: dict[str, str]) -> None:
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
    print(
        f"seeded {email} · workspace {workspace.name} · journey {journey.name} · "
        f"{created} fixture properties added · {evaluated} evaluated against brief v{version.version_no}"
    )


async def main() -> None:
    async with get_sessionmaker()() as db:
        for spec in ACCOUNTS:
            await _seed_account(db, spec)
        await db.commit()
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
