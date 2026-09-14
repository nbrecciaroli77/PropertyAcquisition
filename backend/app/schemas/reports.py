from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


ReportType = Literal["daily", "weekly", "monthly"]
ReleaseKind = Literal["preview", "on_demand", "production"]


class ReportGenerateRequest(Strict):
    release_kind: ReleaseKind = "preview"
    year: int | None = Field(default=None, ge=2020, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    week_start: str | None = Field(default=None, max_length=10)


class ReportRunOut(Strict):
    id: UUID
    journey_id: UUID | None
    report_type: ReportType
    kind: ReleaseKind
    release_state: str
    idempotency_key: str
    period_start: datetime | None
    period_end: datetime | None
    cutoff_at: datetime | None
    timezone: str
    generation_version: str
    is_partial_period: bool
    failure_reason: str | None
    generated_at: datetime | None
    ready_to_send_at: datetime | None
    snapshot: dict[str, Any]
    detail: dict[str, Any]
    created_at: datetime


class ReportPreferenceOut(Strict):
    report_type: ReportType
    enabled: bool
    local_time: str
    weekdays: list[int]
    day_of_week: int | None
    day_of_month: int | None
    timezone: str
    requested_channel: str
    effective_channel: str


class ReportPreferencesOut(Strict):
    daily: ReportPreferenceOut
    weekly: ReportPreferenceOut
    monthly: ReportPreferenceOut


class ReportPreferenceUpdate(Strict):
    enabled: bool
    local_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    weekdays: list[int] = Field(default_factory=list)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    timezone: str = Field(min_length=1, max_length=64)
    requested_channel: Literal["off", "in_app", "email", "both"] = "in_app"
