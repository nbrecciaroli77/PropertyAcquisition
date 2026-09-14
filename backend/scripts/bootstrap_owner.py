"""Production owner bootstrap.

Idempotently creates or verifies the owner account for the private MVP.
Run once after the first deployment (and again after any credential rotation):

    cd /app/backend
    OWNER_EMAIL=<email> OWNER_PASSWORD=<password> python -m scripts.bootstrap_owner

Credentials are read from the environment and never logged. The script:
- Creates the user if they do not exist, or updates the password if they do.
- Pre-verifies the email (no delivery needed) and creates a workspace if absent.
- Locks down the known synthetic demo accounts so their shared password no longer works.
- Records an audit event.
- Cannot be invoked through any public API endpoint.
"""

import asyncio
import os
import secrets
import sys

from dotenv import load_dotenv

load_dotenv()

from app.core.security import hash_password, now_utc  # noqa: E402
from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import Membership, User, Workspace  # noqa: E402
from app.services.outbox import record_audit  # noqa: E402
from app.services.reports import ensure_report_schedule_jobs  # noqa: E402
from sqlalchemy import select  # noqa: E402

# Synthetic demo accounts created by seed.py that must be locked down in production.
_DEMO_DOMAINS = ("propertyacquisition-demo.com",)


def _is_demo_email(email: str) -> bool:
    return any(email.endswith(f"@{d}") for d in _DEMO_DOMAINS)


async def _lock_demo_accounts(db: object) -> int:
    """Set random passwords on demo accounts so shared test credentials no longer work."""
    from sqlalchemy.ext.asyncio import AsyncSession
    assert isinstance(db, AsyncSession)
    demo_users = (
        await db.execute(
            select(User).where(
                User.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    locked = 0
    for u in demo_users:
        if _is_demo_email(u.email):
            u.password_hash = hash_password(secrets.token_urlsafe(32))
            locked += 1
    return locked


async def main() -> None:
    owner_email = os.environ.get("OWNER_EMAIL", "").strip().lower()
    owner_password = os.environ.get("OWNER_PASSWORD", "").strip()

    if not owner_email or not owner_password:
        print(
            "ERROR: OWNER_EMAIL and OWNER_PASSWORD must be supplied as environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(owner_password) < 12:
        print("ERROR: OWNER_PASSWORD must be at least 12 characters.", file=sys.stderr)
        sys.exit(1)

    async with get_sessionmaker()() as db:
        user = (await db.execute(select(User).where(User.email == owner_email))).scalar_one_or_none()

        if user is None:
            user = User(
                email=owner_email,
                password_hash=hash_password(owner_password),
                display_name="Owner",
                email_verified_at=now_utc(),
            )
            db.add(user)
            await db.flush()
            workspace = Workspace(
                name="Owner workspace",
                owner_user_id=user.id,
                timezone="Australia/Perth",
            )
            db.add(workspace)
            await db.flush()
            db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
            await ensure_report_schedule_jobs(db, workspace.id)
            action = "bootstrap.owner_created"
        else:
            user.password_hash = hash_password(owner_password)
            user.email_verified_at = user.email_verified_at or now_utc()
            workspace = (
                await db.execute(select(Workspace).where(Workspace.owner_user_id == user.id))
            ).scalar_one_or_none()
            if workspace is None:
                workspace = Workspace(
                    name="Owner workspace",
                    owner_user_id=user.id,
                    timezone="Australia/Perth",
                )
                db.add(workspace)
                await db.flush()
                db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
                await ensure_report_schedule_jobs(db, workspace.id)
            action = "bootstrap.owner_updated"

        await record_audit(db, action=action, actor_user_id=user.id, workspace_id=workspace.id, subject=owner_email)

        locked = await _lock_demo_accounts(db)
        await db.commit()

    print(f"Bootstrap complete. Action={action}. Demo accounts locked: {locked}.")
    print("The owner password has NOT been logged. Keep it in a secure credential store.")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
