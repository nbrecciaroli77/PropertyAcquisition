from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import FlagState, get_settings
from app.db.base import get_db

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
    email_delivery: str
    flags: dict[str, FlagState]


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    try:
        await db.execute(text("select 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    return HealthResponse(
        status="ok" if database == "connected" else "degraded",
        milestone=settings.milestone,
        database=database,
    )


@router.get("/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    s = get_settings()
    return MetaResponse(
        app_name=s.app_name,
        working_name_status=s.working_name_status,
        gate=s.gate,
        milestone=s.milestone,
        synthetic_data_only=s.synthetic_data_only,
        email_delivery="suppressed_no_provider",
        flags=s.flags,
    )
