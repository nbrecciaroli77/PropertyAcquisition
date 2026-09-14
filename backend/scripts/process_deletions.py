"""Manual-only deletion processor. No scheduler or external delivery is activated."""
import asyncio

from dotenv import load_dotenv

load_dotenv()

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.services.deletion import process_due_deletions  # noqa: E402


async def main() -> None:
    async with get_sessionmaker()() as db:
        outcome = await process_due_deletions(db)
        await db.commit()
    print(outcome)
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
