from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Inherit = Literal["INHERIT"]
LocalTime = str


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_time(value: str) -> str:
    parts = value.split(":")
    if len(parts) != 2 or not all(p.isdigit() and len(p) == 2 for p in parts) or int(parts[0]) > 23 or int(parts[1]) > 59:
        raise ValueError("local_time must be HH:MM (24-hour)")
    return value


class DailyCadence(Strict):
    enabled: bool
    local_time: LocalTime
    weekdays: list[int] = Field(min_length=1, max_length=7)

    _time = field_validator("local_time")(_check_time)

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, value: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in value) or len(set(value)) != len(value):
            raise ValueError("weekdays must be unique values 0 (Monday) to 6 (Sunday)")
        return sorted(value)


class WeeklyCadence(Strict):
    enabled: bool
    local_time: LocalTime
    day_of_week: int = Field(ge=0, le=6)

    _time = field_validator("local_time")(_check_time)


class MonthlyCadence(Strict):
    enabled: bool
    local_time: LocalTime
    day_of_month: int = Field(ge=1, le=28)

    _time = field_validator("local_time")(_check_time)


class Cadence(Strict):
    daily: DailyCadence
    weekly: WeeklyCadence
    monthly: MonthlyCadence


class CampaignSettings(Strict):
    """One configuration layer. Every key defaults to INHERIT (defer to the next layer)."""

    assessment_profile: Inherit | str = Field(default="INHERIT", max_length=40)
    activation_at: Inherit | datetime | None = "INHERIT"
    timezone: Inherit | str = Field(default="INHERIT", max_length=64)
    intake_connection_ref: Inherit | UUID | None = "INHERIT"
    recipient_user_id: Inherit | UUID = "INHERIT"
    delivery_mode: Literal["INHERIT", "separate", "combined"] = "INHERIT"
    cadence: Inherit | Cadence = "INHERIT"


class CampaignSettingsSave(Strict):
    settings: CampaignSettings
    expected_version: int = Field(ge=0)
    reason: str = Field(min_length=3, max_length=400)


class CampaignConfigVersionOut(Strict):
    id: UUID
    scope: str
    version_no: int
    settings: dict[str, Any]
    reason: str
    actor_user_id: UUID | None
    created_at: datetime


class EffectiveSettingOut(BaseModel):
    override: Any
    user_default: Any
    requested: Any
    source: str
    effective: Any
    state: str
    note: str | None = None
    effective_label: str | None = None


class ScheduleSyncOut(Strict):
    report_type: str
    requested_cron: str | None
    configured_cron: str | None
    configured_enabled: bool
    config_drift: bool
    effective_cron: str | None
    next_due_at: datetime | None
    sync_state: str


class CampaignConfigOut(Strict):
    journey_id: UUID
    campaign_kind: str
    campaign_enabled: bool
    settings_owner_user_id: UUID
    campaign_version: int
    user_default_version: int
    settings: dict[str, EffectiveSettingOut]
    schedule: list[ScheduleSyncOut]
    production_scheduler_enabled: bool
    resolved_at: datetime


class UserDefaultsOut(Strict):
    version: int
    settings: dict[str, Any]


class AssessmentProfileOut(Strict):
    id: str
    label: str
    campaign_kinds: list[str]
    available: bool
    engine_version: str | None
    note: str


class ReportLocationOut(Strict):
    report_run_id: UUID
    journey_id: UUID
    report_type: str
