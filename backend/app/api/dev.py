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
from app.db.base import get_db
from app.db.models import OutboxMessage

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
