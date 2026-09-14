"""M4.2 CSV property intake API.

GET  /api/journeys/{id}/intake/csv-template    — download blank CSV template
POST /api/journeys/{id}/intake/csv-preview     — parse + validate, no DB writes
POST /api/journeys/{id}/intake/csv-import      — batch import with idempotency
GET  /api/journeys/{id}/intake/batches/{bid}   — batch status read-back
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.db.base import get_db
from app.db.models import CsvImportBatch
from app.schemas.csv_intake import CsvBatchResult, CsvImportRequest, CsvPreviewResponse
from app.services.csv_intake import (
    generate_template_csv,
    import_csv_batch,
    preview_csv,
)

router = APIRouter(prefix="/journeys/{journey_id}", tags=["csv-intake"])


@router.get(
    "/intake/csv-template",
    summary="Download the CSV import template",
)
async def csv_template(
    journey_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await scoped_journey(journey_id, db, auth.workspace.id)
    content = generate_template_csv()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="property_import_template.csv"'},
    )


@router.post(
    "/intake/csv-preview",
    response_model=CsvPreviewResponse,
    summary="Validate a CSV file without writing any records",
)
async def csv_preview(
    journey_id: uuid.UUID,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> CsvPreviewResponse:
    await scoped_journey(journey_id, db, auth.workspace.id)

    content = await file.read()
    filename = file.filename or "upload.csv"

    try:
        result = preview_csv(content, journey_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.commit()
    return result


@router.post(
    "/intake/csv-import",
    response_model=CsvBatchResult,
    status_code=status.HTTP_200_OK,
    summary="Import a CSV file of properties (idempotent)",
)
async def csv_import(
    journey_id: uuid.UUID,
    file: UploadFile = File(...),
    skip_indices: str = "",
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> CsvBatchResult:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)

    content = await file.read()
    filename = file.filename or "upload.csv"
    skip_row_indices = [int(i) for i in skip_indices.split(",") if i.strip().isdigit()]

    try:
        result = await import_csv_batch(db, journey, auth.user.id, content, filename, skip_row_indices)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return result


@router.get(
    "/intake/batches/{batch_id}",
    response_model=CsvBatchResult,
    summary="Get CSV import batch status",
)
async def get_batch(
    journey_id: uuid.UUID,
    batch_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> CsvBatchResult:
    await scoped_journey(journey_id, db, auth.workspace.id)
    batch = (
        await db.execute(
            select(CsvImportBatch).where(
                CsvImportBatch.id == batch_id,
                CsvImportBatch.workspace_id == auth.workspace.id,
            )
        )
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    await db.commit()
    return CsvBatchResult(
        batch_id=batch.id,
        batch_key=batch.batch_key,
        filename=batch.filename,
        state=batch.state,
        total_rows=batch.row_count,
        created=batch.created_count,
        matched_existing=batch.matched_count,
        requires_review=batch.review_count,
        failed=batch.failed_count,
        skipped=batch.skipped_count,
        row_results=[],
    )
