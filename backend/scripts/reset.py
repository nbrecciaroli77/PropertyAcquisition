"""Destructive reset of prototype data. Run: `python -m scripts.reset --confirm` from /app/backend."""

import asyncio
import sys

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app.db.base import dispose_engine, get_engine  # noqa: E402

TABLES = (
    "audit_events",
    "brief_versions",
    "journeys",
    "outbox_messages",
    "auth_tokens",
    "auth_sessions",
    "login_attempts",
    "memberships",
    "workspaces",
    "users",
)


async def main() -> None:
    if "--confirm" not in sys.argv:
        print("Refusing to reset without --confirm")
        return
    async with get_engine().begin() as conn:
        await conn.execute(text("update journeys set current_version_id = null"))
        for table in TABLES:
            await conn.execute(text(f"delete from {table}"))
    print("reset complete")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
