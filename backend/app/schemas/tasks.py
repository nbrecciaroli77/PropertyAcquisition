from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskOut(Strict):
    id: UUID
    journey_id: UUID
    property_id: UUID | None
    property_address: str | None
    title: str
    notes: str | None
    assignee_user_id: UUID | None
    assignee_name: str | None
    priority: Literal["low", "normal", "high"]
    due_at: datetime | None
    timezone: str
    reminder_offset_minutes: int | None
    status: Literal["open", "completed"]
    done: bool
    done_at: datetime | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    property_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    assignee_user_id: UUID | None = None
    priority: Literal["low", "normal", "high"] = "normal"
    due_at: datetime | None = None
    timezone: str = Field(min_length=1, max_length=64)
    reminder_offset_minutes: int | None = Field(default=None, ge=5, le=10080)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_row_version: int
    property_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    assignee_user_id: UUID | None = None
    priority: Literal["low", "normal", "high"] | None = None
    due_at: datetime | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    reminder_offset_minutes: int | None = Field(default=None, ge=5, le=10080)
    status: Literal["open", "completed"] | None = None


class MemberOut(BaseModel):
    id: UUID
    display_name: str
    email: str
    role: str


class TaskActivityOut(BaseModel):
    id: UUID
    kind: str
    summary: str
    detail: dict[str, Any]
    created_at: datetime