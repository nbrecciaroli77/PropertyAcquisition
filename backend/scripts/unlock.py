"""Clears failed-login lockouts.

`python -m scripts.unlock <email>` clears one account, `python -m scripts.unlock <email> <ip>` also clears
that address bucket, and `python -m scripts.unlock --all` clears every recorded attempt.
"""

import asyncio
import sys

from dotenv import load_dotenv
from sqlalchemy import delete

load_dotenv()

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import LoginAttempt  # noqa: E402


async def main() -> None:
    args = [a for a in sys.argv[1:] if a.strip()]
    if not args:
        print("usage: python -m scripts.unlock <email> [ip] | --all")
        return

    identifiers: list[str] = []
    clear_everything = "--all" in args
    if not clear_everything:
        identifiers.append(f"email:{args[0].strip().lower()}")
        if len(args) > 1:
            identifiers.append(f"ip:{args[1].strip()}")

    async with get_sessionmaker()() as db:
        if clear_everything:
            await db.execute(delete(LoginAttempt))
        else:
            await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier.in_(identifiers)))
        await db.commit()
    print("cleared every recorded login attempt" if clear_everything else f"cleared {', '.join(identifiers)}")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
