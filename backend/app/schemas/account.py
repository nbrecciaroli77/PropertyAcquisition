from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


DeletionRequestType = Literal["leave_workspace", "delete_account", "delete_workspace"]


class DeletionRequestCreate(Strict):
    request_type: DeletionRequestType
    password: str = Field(min_length=1, max_length=200)
    typed_confirmation: str = Field(min_length=1, max_length=40)
    target_workspace_id: UUID | None = None


class DeletionRequestOut(Strict):
    id: UUID
    request_type: DeletionRequestType
    target_workspace_id: UUID | None
    state: str
    detail: dict[str, Any]
    scheduled_execute_at: datetime
    executed_at: datetime | None
    cancelled_at: datetime | None
    failure_reason: str | None
    created_at: datetime
