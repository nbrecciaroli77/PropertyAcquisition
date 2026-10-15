"""U2 evidence: re-running the house assessment with U2 code leaves stored house evaluations byte-identical.

Throwaway DB only (refuses non-loopback via the U1 guard). Run: python memory/u2_house_unchanged_check.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from sqlalchemy import select  # noqa: E402

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import BriefVersion, Journey, MatchEvaluation  # noqa: E402
from app.services.properties import reevaluate_journey  # noqa: E402


def _snap(rows: list[MatchEvaluation]) -> dict[str, tuple]:
    return {
        str(r.id): (r.input_hash, r.verdict, r.fit_pct, r.coverage_pct, r.evaluation_version, r.computed_at.isoformat(),
                    json.dumps(r.result, sort_keys=True))
        for r in rows
    }


async def main() -> None:
    async with get_sessionmaker()() as db:
        houses = (await db.execute(select(Journey).where(Journey.campaign_kind == "house", Journey.current_version_id.is_not(None)))).scalars().all()
        ids = [j.id for j in houses]
        before = _snap((await db.execute(select(MatchEvaluation).where(MatchEvaluation.journey_id.in_(ids)))).scalars().all())
        for j in houses:
            await reevaluate_journey(db, j, await db.get(BriefVersion, j.current_version_id), None)
        await db.flush()
        after = _snap((await db.execute(select(MatchEvaluation).where(MatchEvaluation.journey_id.in_(ids)))).scalars().all())
        await db.rollback()
    changed = [k for k in before if before[k] != after.get(k)]
    print(f"house journeys={len(houses)} evaluations={len(before)} changed={len(changed)} new={len(set(after) - set(before))}")
    await dispose_engine()
    sys.exit(1 if changed else 0)


asyncio.run(main())
