"""Sender-alias review API.  Synthetic fixtures only.

GET   /api/workspaces/me/aliases          — list aliases
PATCH /api/workspaces/me/aliases/{id}     — confirm or reject a single alias
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import SenderAlias

router = APIRouter(prefix="/workspaces/me/aliases", tags=["aliases"])


@router.get("", summary="List sender aliases for workspace")
async def list_aliases(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await db.execute(
            select(SenderAlias).where(SenderAlias.workspace_id == auth.workspace.id)
            .order_by(SenderAlias.created_at)
        )
    ).scalars().all()

    await db.commit()
    return {
        "items": [
            {
                "id": str(a.id),
                "canonical_email": a.canonical_email,
                "alias_email": a.alias_email,
                "display_names_seen": a.display_names_seen,
                "confidence": a.confidence,
                "review_state": a.review_state,
                "first_seen_at": a.first_seen_at.isoformat() if a.first_seen_at else None,
                "evidence_label": a.evidence_label,
                "evidence_url": a.evidence_url,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            }
            for a in rows
        ],
        "total": len(rows),
    }


@router.patch("/{alias_id}", summary="Confirm or reject an alias match")
async def update_alias(
    alias_id: uuid.UUID,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    require_writer(auth)
    action = body.get("action")
    if action not in ("confirm", "reject"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="action must be 'confirm' or 'reject'",
        )

    alias = (
        await db.execute(
            select(SenderAlias).where(
                SenderAlias.id == alias_id,
                SenderAlias.workspace_id == auth.workspace.id,
            )
        )
    ).scalar_one_or_none()
    if alias is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alias not found")

    alias.review_state = "confirmed" if action == "confirm" else "rejected"
    alias.reviewed_at = now_utc()
    alias.reviewed_by_user_id = auth.user.id
    await db.flush()
    await db.commit()

    return {
        "id": str(alias.id),
        "alias_email": alias.alias_email,
        "review_state": alias.review_state,
        "reviewed_at": alias.reviewed_at.isoformat() if alias.reviewed_at else None,
    }
