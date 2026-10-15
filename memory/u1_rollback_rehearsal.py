"""Pre-U1 code against the U1 schema (throwaway DB): proves a code-only rollback keeps working."""
import asyncio

from dotenv import load_dotenv

load_dotenv(".env")

from sqlalchemy import select  # noqa: E402

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import Journey, User, Workspace  # noqa: E402
from app.schemas.intake import FactsIn, IntakeRequest, StructuredPayload  # noqa: E402
from app.services.intake import process_intake  # noqa: E402
from app.services.reports import generate_report  # noqa: E402


async def main() -> None:
    async with get_sessionmaker()() as db:
        user = (await db.execute(select(User).where(User.email == "owner@propertyacquisition-demo.com"))).scalar_one()
        ws = (await db.execute(select(Workspace).where(Workspace.owner_user_id == user.id))).scalar_one()
        house = (await db.execute(select(Journey).where(Journey.workspace_id == ws.id).order_by(Journey.created_at))).scalars().first()
        run = await generate_report(db, journey=house, report_type="weekly", release_kind="preview", requested_by_user_id=user.id)
        print("pre-U1 code on U1 schema: weekly report", run.id, run.release_state)
        result = await process_intake(db, house, user.id, IntakeRequest(mode="structured_form", structured=StructuredPayload(
            address_line="77 Rollback Rehearsal Road", suburb="Example Park", state="WA", facts=FactsIn(land_sqm=500))))
        print("pre-U1 code on U1 schema: intake", result.state)
        journey = Journey(workspace_id=ws.id, name="Rollback rehearsal journey", timezone="Australia/Perth", created_by=user.id, draft_payload={})
        db.add(journey)
        await db.flush()
        print("pre-U1 code on U1 schema: journey insert ok")
        await db.rollback()
    await dispose_engine()


asyncio.run(main())
