"""M4.2 duplicate review API.

GET    /api/workspaces/me/duplicates            — list proposals
GET    /api/workspaces/me/duplicates/{id}       — detail
POST   /api/workspaces/me/duplicates/scan       — run near-duplicate scan
POST   /api/workspaces/me/duplicates/{id}/confirm
POST   /api/workspaces/me/duplicates/{id}/reject
POST   /api/workspaces/me/duplicates/{id}/undo
POST   /api/workspaces/me/duplicates/{id}/split — alias for undo in M4.2
POST   /api/workspaces/me/duplicates/{id}/swap-primary
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import (
    ActivityEvent,
    DiscoveryEvent,
    DuplicateProposal,
    Fact,
    Property,
)
from app.schemas.duplicates import (
    DuplicateActionRequest,
    DuplicateConfirmRequest,
    DuplicateListResponse,
    DuplicateProposalOut,
)
from app.services.duplicates import (
    confirm_merge,
    create_proposal,
    get_proposal_out,
    undo_merge,
)

router = APIRouter(prefix="/workspaces/me/duplicates", tags=["duplicates"])


async def _get_scoped_proposal(
    proposal_id: uuid.UUID,
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> DuplicateProposal:
    p = (
        await db.execute(
            select(DuplicateProposal).where(
                DuplicateProposal.id == proposal_id,
                DuplicateProposal.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return p


@router.get("", response_model=DuplicateListResponse, summary="List duplicate proposals")
async def list_proposals(
    state: str | None = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateListResponse:
    q = select(DuplicateProposal).where(DuplicateProposal.workspace_id == auth.workspace.id)
    if state:
        q = q.where(DuplicateProposal.state == state)
    q = q.order_by(DuplicateProposal.created_at.desc())

    rows = (await db.execute(q)).scalars().all()
    pending_count = sum(1 for r in rows if r.state == "pending")

    items: list[DuplicateProposalOut] = []
    for row in rows:
        try:
            items.append(await get_proposal_out(db, row))
        except Exception:
            pass  # skip orphaned proposals

    await db.commit()
    return DuplicateListResponse(
        items=items,
        pending_count=pending_count,
        total_count=len(items),
    )


@router.get("/{proposal_id}", response_model=DuplicateProposalOut, summary="Get proposal detail")
async def get_proposal(
    proposal_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateProposalOut:
    proposal = await _get_scoped_proposal(proposal_id, auth.workspace.id, db)
    result = await get_proposal_out(db, proposal)
    await db.commit()
    return result


@router.post("/scan", status_code=status.HTTP_200_OK, summary="Scan workspace for near-duplicate properties")
async def scan_duplicates(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Find properties in the same workspace with matching suburb+state+postcode and
    same extracted street number (different full address).  Creates proposals for
    human review.  Never merges automatically."""
    import re

    require_writer(auth)
    _NUMBER_RE = re.compile(r"^(?:[Uu]nit\s+)?(?:\d+[A-Za-z]?(?:/\d+)?\s+)?(\d+)[A-Za-z]?\b")

    props = (
        await db.execute(
            select(Property).where(
                Property.workspace_id == auth.workspace.id,
                Property.merged_into_id.is_(None),
            )
        )
    ).scalars().all()

    created = 0
    seen: set[frozenset] = set()
    for i, p_a in enumerate(props):
        num_a_m = _NUMBER_RE.match(p_a.address_line)
        if not num_a_m:
            continue
        num_a = num_a_m.group(1)
        for p_b in props[i + 1:]:
            if p_a.suburb.lower() != p_b.suburb.lower():
                continue
            if p_a.state != p_b.state:
                continue
            if p_a.postcode != p_b.postcode:
                continue
            num_b_m = _NUMBER_RE.match(p_b.address_line)
            if not num_b_m:
                continue
            if num_a != num_b_m.group(1):
                continue
            if p_a.normalised_address == p_b.normalised_address:
                continue
            pair = frozenset({p_a.id, p_b.id})
            if pair in seen:
                continue
            seen.add(pair)
            try:
                await create_proposal(
                    db, auth.workspace.id, p_a.id, p_b.id, "address_scan",
                    {"street_number": num_a},
                )
                created += 1
            except Exception:
                pass

    await db.commit()
    return {"proposals_created": created}


@router.post("/{proposal_id}/confirm", response_model=DuplicateProposalOut)
async def confirm_proposal(
    proposal_id: uuid.UUID,
    body: DuplicateConfirmRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateProposalOut:
    require_writer(auth)
    proposal = await _get_scoped_proposal(proposal_id, auth.workspace.id, db)
    try:
        proposal = await confirm_merge(
            db, proposal, auth.user.id,
            body.primary_property_id, body.reason, body.row_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    result = await get_proposal_out(db, proposal)
    await db.commit()
    return result


@router.post("/{proposal_id}/reject", response_model=DuplicateProposalOut)
async def reject_proposal(
    proposal_id: uuid.UUID,
    body: DuplicateActionRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateProposalOut:
    require_writer(auth)
    proposal = await _get_scoped_proposal(proposal_id, auth.workspace.id, db)
    if proposal.row_version != body.row_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent edit — refresh and retry")
    if proposal.state not in ("pending", "undone"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Proposal is already {proposal.state}")

    now = now_utc()
    proposal.state = "rejected"
    proposal.actor_user_id = auth.user.id
    proposal.review_reason = body.reason
    proposal.reviewed_at = now
    proposal.row_version += 1
    await db.flush()

    result = await get_proposal_out(db, proposal)
    await db.commit()
    return result


@router.post("/{proposal_id}/undo", response_model=DuplicateProposalOut)
async def undo_proposal(
    proposal_id: uuid.UUID,
    body: DuplicateActionRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateProposalOut:
    require_writer(auth)
    proposal = await _get_scoped_proposal(proposal_id, auth.workspace.id, db)
    try:
        proposal = await undo_merge(
            db, proposal, auth.user.id, body.reason, body.row_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    result = await get_proposal_out(db, proposal)
    await db.commit()
    return result


@router.post("/{proposal_id}/split", response_model=DuplicateProposalOut)
async def split_proposal(
    proposal_id: uuid.UUID,
    body: DuplicateActionRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateProposalOut:
    """Split is equivalent to undo-merge for M4.2."""
    require_writer(auth)
    proposal = await _get_scoped_proposal(proposal_id, auth.workspace.id, db)
    try:
        proposal = await undo_merge(
            db, proposal, auth.user.id,
            body.reason or "Split requested", body.row_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    result = await get_proposal_out(db, proposal)
    await db.commit()
    return result


@router.post("/{proposal_id}/swap-primary", response_model=DuplicateProposalOut)
async def swap_primary(
    proposal_id: uuid.UUID,
    body: DuplicateActionRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> DuplicateProposalOut:
    """Swap which property will survive before confirming the merge."""
    require_writer(auth)
    proposal = await _get_scoped_proposal(proposal_id, auth.workspace.id, db)
    if proposal.row_version != body.row_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent edit — refresh and retry")
    if proposal.state != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Can only swap primary on pending proposals")

    proposal.property_id_a, proposal.property_id_b = proposal.property_id_b, proposal.property_id_a
    proposal.row_version += 1
    await db.flush()

    result = await get_proposal_out(db, proposal)
    await db.commit()
    return result
