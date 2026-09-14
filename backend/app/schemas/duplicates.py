"""Schemas for M4.2 duplicate review API."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PropertySummary(BaseModel):
    id: UUID
    address_line: str
    suburb: str
    state: str
    postcode: str | None
    normalised_address: str
    created_at: datetime | None
    earliest_discovery: datetime | None
    fact_count: int
    merged_into_id: UUID | None


class DuplicateProposalOut(BaseModel):
    id: UUID
    workspace_id: UUID
    property_a: PropertySummary
    property_b: PropertySummary
    state: Literal["pending", "confirmed", "rejected", "undone"]
    proposal_reason: str
    evidence: dict[str, Any]
    unit_suffix_warning: bool
    review_reason: str | None
    actor_user_id: UUID | None
    reviewed_at: datetime | None
    row_version: int
    created_at: datetime | None


class DuplicateActionRequest(BaseModel):
    row_version: int  # optimistic concurrency check
    reason: str | None = Field(default=None, max_length=500)


class DuplicateConfirmRequest(DuplicateActionRequest):
    # User confirms which property survives.
    # If None, defaults to property_id_a (the older one).
    primary_property_id: UUID | None = None


class DuplicateListResponse(BaseModel):
    items: list[DuplicateProposalOut]
    pending_count: int
    total_count: int
