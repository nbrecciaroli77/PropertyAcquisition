from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataExportOut(Strict):
    id: UUID
    export_type: Literal["personal", "workspace"]
    state: str
    file_size_bytes: int
    manifest: dict[str, Any]
    failure_reason: str | None
    expires_at: datetime
    downloaded_at: datetime | None
    download_count: int
    created_at: datetime
