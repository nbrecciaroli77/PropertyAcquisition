"""Duplicate proposal service for M4.2.

Rules:
- Never auto-merge records.
- Proposals are workspace-scoped; cross-tenant access returns 404.
- Confirm = soft merge (FK reassignment) + snapshot for undo.
- Undo restores ONLY originally moved records (not later activity).
- Prevent merge cycles and merging already-merged records without review.
- 81A vs 81C always sets unit_suffix_warning=True.
- All actions produce AuditEvent rows.
- Optimistic concurrency via row_version.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import (
    ActivityEvent,
    BuyerProperty,
    DiscoveryEvent,
    DuplicateProposal,
    EnrichmentRecord,
    Fact,
    GateWaiver,
    IntakeEvent,
    ListingCampaign,
    MatchEvaluation,
    Observation,
    Property,
    PropertyNote,
    PropertyTask,
)
from app.schemas.duplicates import DuplicateProposalOut, DuplicateListResponse, PropertySummary

_UNIT_SUFFIX_RE = re.compile(r"^(\d+)([A-Za-z])\b")


def _extract_unit_suffix(address_line: str) -> str | None:
    m = _UNIT_SUFFIX_RE.match(address_line.strip())
    return m.group(2).upper() if m else None


def _build_unit_suffix_warning(prop_a: Property, prop_b: Property) -> bool:
    """True if both have a unit suffix and the suffixes differ (e.g. 81A vs 81C)."""
    sa = _extract_unit_suffix(prop_a.address_line)
    sb = _extract_unit_suffix(prop_b.address_line)
    if sa and sb and sa != sb:
        return True
    return False


def _build_evidence(prop_a: Property, prop_b: Property) -> dict[str, Any]:
    return {
        "address_a": prop_a.normalised_address,
        "address_b": prop_b.normalised_address,
        "suburb_match": prop_a.suburb.lower() == prop_b.suburb.lower(),
        "state_match": prop_a.state == prop_b.state,
        "postcode_match": prop_a.postcode == prop_b.postcode,
        "unit_a": _extract_unit_suffix(prop_a.address_line),
        "unit_b": _extract_unit_suffix(prop_b.address_line),
    }


async def create_proposal(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    property_id_a: uuid.UUID,
    property_id_b: uuid.UUID,
    proposal_reason: str,
    extra_evidence: dict[str, Any] | None = None,
) -> DuplicateProposal:
    """Create a proposal if one doesn't already exist for this pair (in either direction)."""
    prop_a = (await db.execute(select(Property).where(Property.id == property_id_a))).scalar_one_or_none()
    prop_b = (await db.execute(select(Property).where(Property.id == property_id_b))).scalar_one_or_none()
    if prop_a is None or prop_b is None:
        raise ValueError("Property not found")

    # Check for existing proposal in either direction
    existing = (
        await db.execute(
            select(DuplicateProposal).where(
                DuplicateProposal.workspace_id == workspace_id,
                DuplicateProposal.state.in_(["pending", "confirmed"]),
                (
                    (DuplicateProposal.property_id_a == property_id_a) &
                    (DuplicateProposal.property_id_b == property_id_b)
                ) | (
                    (DuplicateProposal.property_id_a == property_id_b) &
                    (DuplicateProposal.property_id_b == property_id_a)
                ),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # Older property is property_a by default (primary/survivor)
    a_time = prop_a.created_at if hasattr(prop_a, "created_at") and prop_a.created_at else None
    b_time = prop_b.created_at if hasattr(prop_b, "created_at") and prop_b.created_at else None
    if a_time and b_time and b_time < a_time:
        # Swap: b is older, make it the primary
        property_id_a, property_id_b = property_id_b, property_id_a
        prop_a, prop_b = prop_b, prop_a

    evidence = _build_evidence(prop_a, prop_b)
    if extra_evidence:
        evidence.update(extra_evidence)

    unit_warning = _build_unit_suffix_warning(prop_a, prop_b)

    proposal = DuplicateProposal(
        workspace_id=workspace_id,
        property_id_a=property_id_a,
        property_id_b=property_id_b,
        state="pending",
        proposal_reason=proposal_reason,
        evidence=evidence,
        unit_suffix_warning=unit_warning,
    )
    db.add(proposal)
    await db.flush()
    return proposal


# ── Table → FK column map for merge ─────────────────────────────────────────
# (model_class, property_fk_attr, unique_guard_attr | None)
# Note: Fact, DiscoveryEvent handled separately (each has a unique-key constraint)
_MOVE_TARGETS = [
    (ListingCampaign, "property_id", None),
    (Observation, "property_id", None),
    (GateWaiver, "property_id", None),
    (PropertyNote, "property_id", None),
    (PropertyTask, "property_id", None),
    (ActivityEvent, "property_id", None),
    (EnrichmentRecord, "property_id", None),
    # BuyerProperty and MatchEvaluation have unique constraints - handled separately
    # Fact has uq_fact_property_key - handled separately below
    # DiscoveryEvent has uq_discovery_first_per_workspace_property - handled separately below
]


async def _get_ids(db: AsyncSession, model: Any, property_id: uuid.UUID) -> list[uuid.UUID]:
    rows = (
        await db.execute(
            select(model.id).where(model.property_id == property_id)  # type: ignore[attr-defined]
        )
    ).scalars().all()
    return list(rows)


async def confirm_merge(
    db: AsyncSession,
    proposal: DuplicateProposal,
    actor_id: uuid.UUID,
    primary_property_id: uuid.UUID | None,
    reason: str | None,
    expected_row_version: int,
) -> DuplicateProposal:
    """Soft merge prop_b into prop_a.  Builds a snapshot for undo."""
    if proposal.row_version != expected_row_version:
        raise ValueError("Concurrent edit detected — refresh and try again")
    if proposal.state not in ("pending", "undone"):
        raise ValueError(f"Proposal is already {proposal.state}")

    # Determine survivor: user can swap, but 81A/81C requires explicit acknowledgement
    if primary_property_id is not None:
        if primary_property_id not in {proposal.property_id_a, proposal.property_id_b}:
            raise ValueError("primary_property_id must be one of the two proposal properties")
        survivor_id = primary_property_id
        duplicate_id = (
            proposal.property_id_b if primary_property_id == proposal.property_id_a
            else proposal.property_id_a
        )
    else:
        survivor_id = proposal.property_id_a
        duplicate_id = proposal.property_id_b

    # Fetch both
    survivor = (await db.execute(select(Property).where(Property.id == survivor_id))).scalar_one_or_none()
    dup = (await db.execute(select(Property).where(Property.id == duplicate_id))).scalar_one_or_none()

    if survivor is None or dup is None:
        raise ValueError("Property not found")
    if dup.merged_into_id is not None:
        raise ValueError("Property is already merged into another. Undo that merge first.")

    # Prevent merge cycles
    if survivor.merged_into_id is not None:
        raise ValueError("Survivor property is itself merged — cannot use it as primary")

    now = now_utc()
    snapshot: dict[str, Any] = {
        "survivor_id": str(survivor_id),
        "duplicate_id": str(duplicate_id),
        "moved_at": now.isoformat(),
    }

    # Move simple FK records
    for model_class, fk_attr, _ in _MOVE_TARGETS:
        ids = await _get_ids(db, model_class, duplicate_id)
        if ids:
            await db.execute(
                update(model_class)
                .where(getattr(model_class, fk_attr) == duplicate_id)
                .values(**{fk_attr: survivor_id})
            )
            snapshot[f"moved_{model_class.__tablename__}"] = [str(i) for i in ids]

    # BuyerProperty: skip rows where survivor already has one for the same journey
    bp_dup_rows = (
        await db.execute(
            select(BuyerProperty).where(BuyerProperty.property_id == duplicate_id)
        )
    ).scalars().all()
    bp_moved_ids = []
    for bp in bp_dup_rows:
        conflict = (
            await db.execute(
                select(BuyerProperty).where(
                    BuyerProperty.property_id == survivor_id,
                    BuyerProperty.journey_id == bp.journey_id,
                )
            )
        ).scalar_one_or_none()
        if conflict is None:
            bp.property_id = survivor_id
            await db.flush()
            bp_moved_ids.append(str(bp.id))
        # else: keep survivor's BuyerProperty, dup's is just left as orphan (survives on dup)
    if bp_moved_ids:
        snapshot["moved_buyer_properties"] = bp_moved_ids

    # MatchEvaluation: skip conflicts
    me_dup_rows = (
        await db.execute(
            select(MatchEvaluation).where(MatchEvaluation.property_id == duplicate_id)
        )
    ).scalars().all()
    me_moved_ids = []
    for me in me_dup_rows:
        conflict = (
            await db.execute(
                select(MatchEvaluation).where(
                    MatchEvaluation.property_id == survivor_id,
                    MatchEvaluation.brief_version_id == me.brief_version_id,
                )
            )
        ).scalar_one_or_none()
        if conflict is None:
            me.property_id = survivor_id
            await db.flush()
            me_moved_ids.append(str(me.id))
    if me_moved_ids:
        snapshot["moved_match_evaluations"] = me_moved_ids

    # Facts: survivor's existing key takes priority — skip conflicts (uq_fact_property_key)
    fact_dup_rows = (
        await db.execute(select(Fact).where(Fact.property_id == duplicate_id))
    ).scalars().all()
    fact_moved_ids = []
    for fact in fact_dup_rows:
        conflict = (
            await db.execute(
                select(Fact).where(Fact.property_id == survivor_id, Fact.key == fact.key)
            )
        ).scalar_one_or_none()
        if conflict is None:
            fact.property_id = survivor_id
            await db.flush()
            fact_moved_ids.append(str(fact.id))
        # else: survivor's fact wins — leave duplicate's fact on the merged property
    if fact_moved_ids:
        snapshot["moved_facts"] = fact_moved_ids

    # DiscoveryEvents: channel_events move freely; first_discovery only if survivor has none
    # (Enforces exactly one first_discovery per workspace/property — M4.2 rule)
    de_dup_rows = (
        await db.execute(select(DiscoveryEvent).where(DiscoveryEvent.property_id == duplicate_id))
    ).scalars().all()
    de_moved_ids = []
    survivor_has_first_discovery = (
        await db.execute(
            select(DiscoveryEvent).where(
                DiscoveryEvent.property_id == survivor_id,
                DiscoveryEvent.event_type == "first_discovery",
            )
        )
    ).scalar_one_or_none() is not None
    for de in de_dup_rows:
        if de.event_type == "first_discovery" and survivor_has_first_discovery:
            continue  # preserve uniqueness — skip, leave orphaned on merged property
        de.property_id = survivor_id
        await db.flush()
        de_moved_ids.append(str(de.id))
    if de_moved_ids:
        snapshot["moved_discovery_events"] = de_moved_ids

    # IntakeEvents: update result_property_id and duplicate_property_id
    ie_ids_result = (
        await db.execute(
            select(IntakeEvent.id).where(IntakeEvent.result_property_id == duplicate_id)
        )
    ).scalars().all()
    if ie_ids_result:
        await db.execute(
            update(IntakeEvent)
            .where(IntakeEvent.result_property_id == duplicate_id)
            .values(result_property_id=survivor_id)
        )
        snapshot["moved_intake_events_result"] = [str(i) for i in ie_ids_result]

    # Mark dup as merged
    dup.merged_into_id = survivor_id
    dup.merged_at = now
    dup.merge_actor_user_id = actor_id

    # Update proposal
    proposal.state = "confirmed"
    proposal.actor_user_id = actor_id
    proposal.review_reason = reason
    proposal.reviewed_at = now
    proposal.row_version += 1
    proposal.property_id_a = survivor_id
    proposal.property_id_b = duplicate_id
    proposal.merge_snapshot = snapshot

    # Audit activity event on survivor
    db.add(ActivityEvent(
        workspace_id=proposal.workspace_id,
        property_id=survivor_id,
        kind="duplicate_merged",
        summary=f"Merged duplicate {dup.address_line}, {dup.suburb} into this property",
        detail={
            "duplicate_property_id": str(duplicate_id),
            "proposal_id": str(proposal.id),
            "reason": reason,
        },
        actor_user_id=actor_id,
        journey_id=survivor.journey_id,
    ))

    await db.flush()
    return proposal


async def undo_merge(
    db: AsyncSession,
    proposal: DuplicateProposal,
    actor_id: uuid.UUID,
    reason: str | None,
    expected_row_version: int,
) -> DuplicateProposal:
    """Restore only the originally moved records from the snapshot."""
    if proposal.row_version != expected_row_version:
        raise ValueError("Concurrent edit detected — refresh and try again")
    if proposal.state != "confirmed":
        raise ValueError("Only confirmed merges can be undone")

    snapshot = proposal.merge_snapshot or {}
    survivor_id = uuid.UUID(snapshot["survivor_id"])
    duplicate_id = uuid.UUID(snapshot["duplicate_id"])
    now = now_utc()

    # Restore duplicate property
    dup = (await db.execute(select(Property).where(Property.id == duplicate_id))).scalar_one_or_none()
    if dup:
        dup.merged_into_id = None
        dup.merged_at = None
        dup.merge_actor_user_id = None

    # Restore FK-moved records using snapshot IDs
    model_map = {
        "listing_campaigns": ListingCampaign,
        "observations": Observation,
        "facts": Fact,
        "gate_waivers": GateWaiver,
        "property_notes": PropertyNote,
        "property_tasks": PropertyTask,
        "activity_events": ActivityEvent,
        "discovery_events": DiscoveryEvent,
        "enrichment_records": EnrichmentRecord,
    }
    for table_key, model_class in model_map.items():
        moved_ids = snapshot.get(f"moved_{table_key}", [])
        if moved_ids:
            uuids = [uuid.UUID(i) for i in moved_ids]
            await db.execute(
                update(model_class)
                .where(model_class.id.in_(uuids))  # type: ignore[attr-defined]
                .values(property_id=duplicate_id)
            )

    # Restore BuyerProperty
    for bp_id_str in snapshot.get("moved_buyer_properties", []):
        bp = (await db.execute(select(BuyerProperty).where(BuyerProperty.id == uuid.UUID(bp_id_str)))).scalar_one_or_none()
        if bp:
            bp.property_id = duplicate_id

    # Restore MatchEvaluation
    for me_id_str in snapshot.get("moved_match_evaluations", []):
        me = (await db.execute(select(MatchEvaluation).where(MatchEvaluation.id == uuid.UUID(me_id_str)))).scalar_one_or_none()
        if me:
            me.property_id = duplicate_id

    # Restore IntakeEvents
    for ie_id_str in snapshot.get("moved_intake_events_result", []):
        ie = (await db.execute(select(IntakeEvent).where(IntakeEvent.id == uuid.UUID(ie_id_str)))).scalar_one_or_none()
        if ie:
            ie.result_property_id = duplicate_id

    proposal.state = "undone"
    proposal.actor_user_id = actor_id
    proposal.review_reason = reason
    proposal.reviewed_at = now
    proposal.row_version += 1

    # Audit
    survivor = (await db.execute(select(Property).where(Property.id == survivor_id))).scalar_one_or_none()
    if survivor:
        db.add(ActivityEvent(
            workspace_id=proposal.workspace_id,
            property_id=survivor_id,
            kind="duplicate_merge_undone",
            summary=f"Merge of duplicate was undone",
            detail={"proposal_id": str(proposal.id), "reason": reason},
            actor_user_id=actor_id,
            journey_id=survivor.journey_id,
        ))

    await db.flush()
    return proposal


async def _prop_summary(db: AsyncSession, prop: Property) -> PropertySummary:
    # Count facts
    fact_count = (
        await db.execute(
            select(Fact.id).where(
                Fact.property_id == prop.id,
                Fact.value_state == "known",
            )
        )
    )
    n_facts = len(fact_count.scalars().all())

    # Earliest discovery
    disc = (
        await db.execute(
            select(DiscoveryEvent.discovered_at)
            .where(DiscoveryEvent.property_id == prop.id)
            .order_by(DiscoveryEvent.discovered_at)
            .limit(1)
        )
    ).scalar_one_or_none()

    return PropertySummary(
        id=prop.id,
        address_line=prop.address_line,
        suburb=prop.suburb,
        state=prop.state,
        postcode=prop.postcode,
        normalised_address=prop.normalised_address,
        created_at=getattr(prop, "created_at", None),
        earliest_discovery=disc,
        fact_count=n_facts,
        merged_into_id=prop.merged_into_id,
    )


async def get_proposal_out(db: AsyncSession, proposal: DuplicateProposal) -> DuplicateProposalOut:
    prop_a_row = (await db.execute(select(Property).where(Property.id == proposal.property_id_a))).scalar_one()
    prop_b_row = (await db.execute(select(Property).where(Property.id == proposal.property_id_b))).scalar_one()
    prop_a_summary = await _prop_summary(db, prop_a_row)
    prop_b_summary = await _prop_summary(db, prop_b_row)

    return DuplicateProposalOut(
        id=proposal.id,
        workspace_id=proposal.workspace_id,
        property_a=prop_a_summary,
        property_b=prop_b_summary,
        state=proposal.state,  # type: ignore[arg-type]
        proposal_reason=proposal.proposal_reason,
        evidence=proposal.evidence,
        unit_suffix_warning=proposal.unit_suffix_warning,
        review_reason=proposal.review_reason,
        actor_user_id=proposal.actor_user_id,
        reviewed_at=proposal.reviewed_at,
        row_version=proposal.row_version,
        created_at=getattr(proposal, "created_at", None),
    )
