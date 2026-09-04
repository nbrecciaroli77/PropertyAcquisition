from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import FlagState, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    milestone: int
    database: str


class MetaResponse(BaseModel):
    app_name: str
    working_name_status: str
    gate: str
    milestone: int
    synthetic_data_only: bool
    flags: dict[str, FlagState]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", milestone=settings.milestone, database="not_configured")


@router.get("/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    s = get_settings()
    return MetaResponse(
        app_name=s.app_name,
        working_name_status=s.working_name_status,
        gate=s.gate,
        milestone=s.milestone,
        synthetic_data_only=s.synthetic_data_only,
        flags=s.flags,
    )
