"""redact_outbox.py — one-shot security remediation script.

Invalidates every unused AuthToken (verify_email + password_reset) and
removes every OutboxMessage row so that previously captured token URLs
cannot be replayed and recipient addresses / message bodies are no longer
retrievable even if an inspection route were accidentally re-enabled.

Seeded demonstration accounts are unaffected because their email
verification tokens were consumed during seed and carry a non-NULL used_at.

Usage (run once after deploying the DEV_ROUTES_ENABLED=false change):
    cd /app/backend && python -m scripts.redact_outbox --confirm
"""

import asyncio
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import update, delete  # noqa: E402

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import AuthToken, OutboxMessage  # noqa: E402


async def _run(dry_run: bool) -> None:
    now = datetime.now(timezone.utc)
    async with get_sessionmaker()() as db:
        # 1. Expire every auth token that has not been consumed yet.
        #    Sets used_at = now so _consume_token will reject them.
        result_tokens = await db.execute(
            update(AuthToken)
            .where(AuthToken.used_at.is_(None))
            .values(used_at=now)
        )
        tokens_invalidated = result_tokens.rowcount

        # 2. Delete all outbox messages (recipient addresses, bodies, action_urls).
        result_outbox = await db.execute(delete(OutboxMessage))
        outbox_deleted = result_outbox.rowcount

        if dry_run:
            print(f"[DRY RUN] Would invalidate {tokens_invalidated} token(s).")
            print(f"[DRY RUN] Would delete {outbox_deleted} outbox message(s).")
            await db.rollback()
        else:
            await db.commit()
            print(f"[OK] Invalidated {tokens_invalidated} outstanding token(s).")
            print(f"[OK] Deleted {outbox_deleted} outbox message(s).")

    await dispose_engine()


def main() -> None:
    confirm = "--confirm" in sys.argv
    dry_run = not confirm
    if dry_run:
        print("Running in DRY-RUN mode. Pass --confirm to apply changes.")
    asyncio.run(_run(dry_run))


if __name__ == "__main__":
    main()
