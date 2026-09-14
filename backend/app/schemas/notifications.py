from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


NotificationChannel = Literal["off", "in_app", "email", "both"]


class NotificationOut(Strict):
    id: UUID
    event_id: UUID
    category: str
    title: str
    message: str
    priority: str
    safe_deep_link: str
    property_id: UUID | None
    property_address: str | None
    property_image_url: str | None
    task_id: UUID | None
    source_event_id: UUID | None
    report_run_id: UUID | None
    evidence_ref: dict[str, Any]
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None
    expires_at: datetime | None
    is_expired: bool


class NotificationListOut(Strict):
    items: list[NotificationOut]
    unread_count: int


class NotificationPreferenceOut(Strict):
    category: str | None
    requested_channel: NotificationChannel
    effective_channel: NotificationChannel
    global_in_app_enabled: bool
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    timezone: str
    due_soon_minutes: int
    report_daily_enabled: bool
    report_weekly_enabled: bool
    report_monthly_enabled: bool
    report_preferences_active: bool
    email_provider_connected: bool


class PreferencesOut(Strict):
    global_settings: NotificationPreferenceOut
    categories: list[NotificationPreferenceOut]


class GlobalPreferenceUpdate(Strict):
    in_app_enabled: bool
    quiet_hours_start: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(min_length=1, max_length=64)
    due_soon_minutes: int = Field(ge=5, le=10080)
    report_daily_enabled: bool = False
    report_weekly_enabled: bool = False
    report_monthly_enabled: bool = False


class CategoryPreferenceUpdate(Strict):
    requested_channel: NotificationChannel


class NotificationStateUpdate(Strict):
    read: bool | None = None
    dismissed: bool | None = None