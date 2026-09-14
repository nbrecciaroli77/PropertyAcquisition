import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import DataExport
from app.schemas.exports import DataExportOut
from app.services.exports import create_export, purge_expired_exports
from app.services.outbox import record_audit

router = APIRouter(prefix="/exports", tags=["exports"])


def _out(export: DataExport) -> DataExportOut:
    return DataExportOut(
        id=export.id, export_type=export.export_type, state=export.state, file_size_bytes=export.file_size_bytes,
        manifest=export.manifest, failure_reason=export.failure_reason, expires_at=export.expires_at,
        downloaded_at=export.downloaded_at, download_count=export.download_count, created_at=export.created_at,
    )


@router.get("", response_model=list[DataExportOut])
async def list_exports(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> list[DataExportOut]:
    await purge_expired_exports(db)
    rows = (
        await db.execute(
            select(DataExport)
            .where(DataExport.requested_by_user_id == auth.user.id, DataExport.workspace_id == auth.workspace.id)
            .order_by(DataExport.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    await db.commit()
    return [_out(r) for r in rows]


@router.post("/personal", response_model=DataExportOut, status_code=status.HTTP_201_CREATED)
async def export_personal(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> DataExportOut:
    export = await create_export(db, requested_by=auth.user, workspace=auth.workspace, export_type="personal")
    await record_audit(db, action="export.personal_requested", actor_user_id=auth.user.id, workspace_id=auth.workspace.id, subject=str(export.id))
    await db.commit()
    await db.refresh(export)
    return _out(export)


@router.post("/workspace", response_model=DataExportOut, status_code=status.HTTP_201_CREATED)
async def export_workspace(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> DataExportOut:
    if auth.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace owner can export workspace data.")
    export = await create_export(db, requested_by=auth.user, workspace=auth.workspace, export_type="workspace")
    await record_audit(db, action="export.workspace_requested", actor_user_id=auth.user.id, workspace_id=auth.workspace.id, subject=str(export.id))
    await db.commit()
    await db.refresh(export)
    return _out(export)


@router.get("/{export_id}/download")
async def download_export(export_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> Response:
    export = (
        await db.execute(
            select(DataExport).where(DataExport.id == export_id, DataExport.requested_by_user_id == auth.user.id, DataExport.workspace_id == auth.workspace.id)
        )
    ).scalar_one_or_none()
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    if export.state != "ready" or export.expires_at <= now_utc() or export.file_data is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This export has expired. Request a new one.")
    export.downloaded_at = now_utc()
    export.download_count += 1
    await record_audit(db, action="export.downloaded", actor_user_id=auth.user.id, workspace_id=auth.workspace.id, subject=str(export.id))
    await db.commit()
    filename = f"property-acquisition-{export.export_type}-export.zip"
    return Response(content=export.file_data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
