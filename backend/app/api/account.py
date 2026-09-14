import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth
from app.db.base import get_db
from app.db.models import DeletionRequest
from app.schemas.account import DeletionRequestCreate, DeletionRequestOut
from app.services.deletion import cancel_deletion_request, create_deletion_request

router = APIRouter(prefix="/account", tags=["account"])


def _out(request: DeletionRequest) -> DeletionRequestOut:
    return DeletionRequestOut(
        id=request.id, request_type=request.request_type, target_workspace_id=request.target_workspace_id,
        state=request.state, detail=request.detail, scheduled_execute_at=request.scheduled_execute_at,
        executed_at=request.executed_at, cancelled_at=request.cancelled_at, failure_reason=request.failure_reason,
        created_at=request.created_at,
    )


@router.get("/deletion-requests", response_model=list[DeletionRequestOut])
async def list_deletion_requests(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> list[DeletionRequestOut]:
    rows = (
        await db.execute(select(DeletionRequest).where(DeletionRequest.requested_by_user_id == auth.user.id).order_by(DeletionRequest.created_at.desc()))
    ).scalars().all()
    return [_out(r) for r in rows]


@router.post("/deletion-requests", response_model=DeletionRequestOut, status_code=status.HTTP_201_CREATED)
async def request_deletion(
    body: DeletionRequestCreate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> DeletionRequestOut:
    request = await create_deletion_request(
        db, auth=auth, request_type=body.request_type, password=body.password,
        typed_confirmation=body.typed_confirmation, target_workspace_id=body.target_workspace_id,
    )
    await db.commit()
    await db.refresh(request)
    return _out(request)


@router.post("/deletion-requests/{request_id}/cancel", response_model=DeletionRequestOut)
async def cancel_deletion(
    request_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> DeletionRequestOut:
    request = await cancel_deletion_request(db, auth=auth, request_id=request_id)
    await db.commit()
    return _out(request)
