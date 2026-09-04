"""Idempotent synthetic seed. Run: `python -m scripts.seed` from /app/backend.

Creates two independent workspaces so cross-tenant isolation can be demonstrated. No live data.
"""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

from app.core.security import hash_password, now_utc  # noqa: E402
from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import BriefVersion, Journey, Membership, User, Workspace  # noqa: E402
from app.schemas.brief import Area, BriefPayload, default_brief  # noqa: E402

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
    brief = default_brief()
    brief.budget.ceiling_minor = 1_250_000_00
    brief.budget.preferred_min_minor = 950_000_00
    brief.budget.preferred_max_minor = 1_150_000_00
    brief.property_profile.types = ["house"]
    brief.property_profile.detached_required = True
    brief.beds.min = 4
    brief.baths.min = 2
    brief.parking.min = 2
    brief.land_sqm.min = 400
    brief.renovation.level = "cosmetic"
    brief.timing.horizon = "6_months"
    brief.locations.states = ["WA"]
    brief.locations.included = [
        Area(suburb="Wembley Downs", state="WA", postcode="6019"),
        Area(suburb="Woodlands", state="WA", postcode="6018"),
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
    print(f"seeded {email} · workspace {workspace.name} · journey {journey.name}")


async def main() -> None:
    async with get_sessionmaker()() as db:
        for spec in ACCOUNTS:
            await _seed_account(db, spec)
        await db.commit()
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
