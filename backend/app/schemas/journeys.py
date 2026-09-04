from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.brief import BriefPayload, FieldError


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JourneyCreate(Strict):
    name: str = Field(min_length=1, max_length=160)
    timezone: str = Field(default="Australia/Perth", max_length=64)


class JourneyUpdate(Strict):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    timezone: str | None = Field(default=None, max_length=64)
    onboarding_step: int | None = Field(default=None, ge=1, le=6)
    status: Literal["onboarding", "active", "archived"] | None = None
    expected_row_version: int


class JourneyOut(Strict):
    id: UUID
    name: str
    status: str
    timezone: str
    onboarding_step: int
    onboarding_complete: bool
    row_version: int
    current_version_no: int | None
    published_versions: int
    created_at: datetime
    updated_at: datetime


class BriefVersionOut(Strict):
    id: UUID
    version_no: int
    reason: str
    published_at: datetime
    actor_email: str
    reevaluation_state: str
    payload: BriefPayload


class DraftSave(Strict):
    payload: BriefPayload
    expected_row_version: int
    onboarding_step: int | None = Field(default=None, ge=1, le=6)


class PublishRequest(Strict):
    reason: str = Field(min_length=3, max_length=400)
    expected_row_version: int


class BriefOut(Strict):
    journey: JourneyOut
    draft: BriefPayload
    draft_updated_at: datetime
    validation: list[FieldError]
    current_version: BriefVersionOut | None
    weight_total_enabled: int
