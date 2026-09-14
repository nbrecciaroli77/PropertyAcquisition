from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BuyerState = Literal[
    "reviewing",
    "shortlisted",
    "inspection_considered",
    "inspected",
    "due_diligence",
    "offer_preparation",
    "offer_submitted",
    "under_contract",
    "settled",
    "rejected",
    "archived",
]

InspectionResult = Literal["not_inspected", "feedback_pending", "great", "ok", "not_as_good"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactOut(Strict):
    key: str
    value_state: str
    value_int: int | None
    value_text: str | None
    value_bool: bool | None
    source_kind: str
    source_label: str
    observed_at: datetime
    checked_at: datetime
    freshness: str
    confidence: str
    conflict_note: str | None


class CampaignOut(Strict):
    id: UUID
    source_label: str
    market_state: str
    price_kind: str
    raw_price: str
    lower_minor: int | None
    upper_minor: int | None
    currency: str
    price_source: str
    last_checked_at: datetime
    freshness: str


class ObservationOut(Strict):
    id: UUID
    source_kind: str
    source_label: str
    observed_at: datetime
    checked_at: datetime
    freshness: str
    note: str | None


class EvaluationOut(Strict):
    id: UUID
    brief_version_no: int
    evaluation_version: str
    input_hash: str
    verdict: str
    route: str
    fit: dict[str, Any]
    coverage: dict[str, Any]
    gates: list[dict[str, Any]]
    components: list[dict[str, Any]]
    computed_at: datetime


class WaiverOut(Strict):
    id: UUID
    criterion: str
    reason: str
    actor_email: str
    created_at: datetime


class NoteOut(Strict):
    id: UUID
    body: str
    author_email: str
    row_version: int
    created_at: datetime
    updated_at: datetime


class TaskOut(Strict):
    id: UUID
    title: str
    done: bool
    done_at: datetime | None
    row_version: int
    created_at: datetime


class ActivityOut(Strict):
    id: UUID
    kind: str
    summary: str
    detail: dict[str, Any]
    actor_email: str | None
    property_id: UUID | None
    created_at: datetime


class PropertySummary(Strict):
    id: UUID
    legacy_ref: str | None
    address_line: str
    unit: str | None
    suburb: str
    state: str
    postcode: str | None
    synthetic: bool
    image_url: str | None
    image_attribution: str | None
    campaign: CampaignOut | None
    facts: dict[str, FactOut]
    buyer_state: str
    saved: bool
    buyer_row_version: int
    evaluation: EvaluationOut | None
    waived_criteria: list[str]
    allowed_transitions: list[str]
    inspection_state: str
    inspection_note: str | None
    inspection_recorded_at: datetime | None
    updated_at: datetime


class PropertyDetail(PropertySummary):
    observations: list[ObservationOut]
    waivers: list[WaiverOut]
    notes: list[NoteOut]
    tasks: list[TaskOut]
    activity: list[ActivityOut]
    row_version: int


class StageChange(Strict):
    to_state: BuyerState
    expected_row_version: int


class SavedChange(Strict):
    saved: bool
    expected_row_version: int


class InspectionChange(Strict):
    inspection_state: InspectionResult
    inspection_note: str | None = Field(default=None, max_length=1000)
    expected_row_version: int


class WaiverCreate(Strict):
    criterion: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=5, max_length=400)


class NoteCreate(Strict):
    body: str = Field(min_length=1, max_length=4000)


class NoteUpdate(Strict):
    body: str = Field(min_length=1, max_length=4000)
    expected_row_version: int


class TaskCreate(Strict):
    title: str = Field(min_length=1, max_length=200)


class TaskUpdate(Strict):
    done: bool
    expected_row_version: int


class TodayOut(Strict):
    journey_id: UUID
    brief_version_no: int | None
    total_properties: int
    eligible_reviewing: int
    verification_required: int
    known_failures: int
    fit_available: int
    under_offer_market: int
    changes: list[ActivityOut]
    open_tasks: int
    attention: list[PropertySummary]


class LoadDemoRequest(Strict):
    journey_id: UUID
