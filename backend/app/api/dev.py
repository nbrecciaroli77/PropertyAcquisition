"""Development-only outbox inspection.

No email provider is configured, so verification and reset links never leave the database.
This route exposes them for the owner's own review and is hard-disabled outside development.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.db.base import get_db
from app.db.models import BriefVersion, OutboxMessage
from app.services.properties import load_demo_properties, reevaluate_journey

router = APIRouter(prefix="/dev", tags=["dev"])


class OutboxOut(BaseModel):
    id: UUID
    to_email: str
    kind: str
    subject: str
    body_text: str
    action_url: str | None
    delivery_state: str
    created_at: datetime


@router.get("/outbox", response_model=list[OutboxOut])
async def list_outbox(email: str | None = None, db: AsyncSession = Depends(get_db)) -> list[OutboxOut]:
    if not get_settings().is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    query = select(OutboxMessage).order_by(OutboxMessage.created_at.desc()).limit(50)
    if email:
        query = query.where(OutboxMessage.to_email == email.strip().lower())
    rows = (await db.execute(query)).scalars()
    return [
        OutboxOut(
            id=m.id,
            to_email=m.to_email,
            kind=m.kind,
            subject=m.subject,
            body_text=m.body_text,
            action_url=m.action_url,
            delivery_state=m.delivery_state,
            created_at=m.created_at,
        )
        for m in rows
    ]


class LoadDemoIn(BaseModel):
    journey_id: UUID


@router.post("/load-demo-properties", status_code=status.HTTP_201_CREATED)
async def load_demo(
    body: LoadDemoIn, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> dict[str, int | str]:
    """Development-only fixture creation from fixtures/demo-data.json. Not the Add property intake."""
    if not get_settings().is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    require_writer(auth)
    journey = await scoped_journey(body.journey_id, db, auth.workspace.id)
    created = await load_demo_properties(db, journey, auth.user.id)
    version = None
    if journey.current_version_id is not None:
        version = (
            await db.execute(select(BriefVersion).where(BriefVersion.id == journey.current_version_id))
        ).scalar_one()
        await reevaluate_journey(db, journey, version, auth.user.id)
    await db.commit()
    return {"created": created, "evaluated_against": version.version_no if version else "no published brief"}
