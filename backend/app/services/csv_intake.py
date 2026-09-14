"""CSV intake service for M4.2.

Rules:
- No URL fetching from CSV cells.
- Formula injection: cells starting with =, +, -, @ are treated as inert text,
  flagged for review, stored as evidence, never executed.
- Batch idempotency: SHA256(file_bytes + journey_id) prevents duplicate import.
- File limits: 1 MB / 200 rows (private MVP).
- Every valid row goes through the canonical process_intake pipeline.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import CsvImportBatch, Journey
from app.schemas.csv_intake import CsvBatchResult, CsvPreviewResponse, CsvPreviewRow
from app.schemas.intake import FactsIn, IntakeRequest, PriceIn, StructuredPayload

MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_ROWS = 200

REQUIRED_HEADERS = {"address_line", "suburb", "state"}
OPTIONAL_HEADERS = {
    "postcode", "beds", "baths", "cars", "land_sqm", "floor_sqm",
    "property_type", "raw_price", "price_kind", "notes",
}
ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

# Valid AU states
_AU_STATES = {"WA", "SA", "NT", "QLD", "NSW", "ACT", "VIC", "TAS"}

# Formula-injection detection
_FORMULA_PREFIXES = ("=", "+", "-", "@")

_VALID_PROPERTY_TYPES = {
    "house", "townhouse", "villa", "unit", "apartment", "land", "acreage",
}
_VALID_PRICE_KINDS = {
    "exact", "range", "from", "offers_over", "auction",
    "contact_agent", "expressions_of_interest", "conflicting",
}


def _derive_batch_key(file_bytes: bytes, journey_id: uuid.UUID) -> str:
    raw = f"{journey_id}:".encode() + file_bytes
    return hashlib.sha256(raw).hexdigest()


def _is_formula(value: str) -> bool:
    return bool(value) and value[0] in _FORMULA_PREFIXES


def _sanitise(value: str) -> tuple[str, bool]:
    """Return (sanitised_value, was_formula).  Formula values are preserved as inert text."""
    stripped = value.strip()
    if _is_formula(stripped):
        return stripped, True
    return stripped, False


def _parse_int(value: str) -> tuple[int | None, str | None]:
    """Returns (int | None, error_message | None)."""
    if not value:
        return None, None
    try:
        n = int(value)
        if n < 0:
            return None, f"must be non-negative, got {value!r}"
        return n, None
    except ValueError:
        return None, f"expected integer, got {value!r}"


def _validate_row(raw: dict[str, str], row_index: int) -> CsvPreviewRow:
    errors: list[str] = []
    warnings: list[str] = []
    formula_flags: list[str] = []

    def _get(col: str) -> str:
        val, is_formula = _sanitise(raw.get(col, ""))
        if is_formula:
            formula_flags.append(col)
            warnings.append(
                f"Column '{col}' begins with {val[0]!r} — treated as inert text, flagged for review"
            )
        return val

    address_line = _get("address_line")
    suburb = _get("suburb")
    state = _get("state").upper()
    postcode = _get("postcode") or None
    notes = _get("notes") or None

    if not address_line:
        errors.append("address_line is required")
    elif len(address_line) < 2:
        errors.append("address_line is too short")

    if not suburb:
        errors.append("suburb is required")

    if not state:
        errors.append("state is required")
    elif state not in _AU_STATES:
        errors.append(f"state '{state}' is not a recognised AU state/territory")

    if postcode and not re.fullmatch(r"\d{4}", postcode):
        warnings.append(f"postcode '{postcode}' doesn't look like a 4-digit postcode")

    # Integer fields
    beds_val, beds_err = _parse_int(_get("beds"))
    baths_val, baths_err = _parse_int(_get("baths"))
    cars_val, cars_err = _parse_int(_get("cars"))
    land_val, land_err = _parse_int(_get("land_sqm"))
    floor_val, floor_err = _parse_int(_get("floor_sqm"))

    for err in [beds_err, baths_err, cars_err, land_err, floor_err]:
        if err:
            warnings.append(err)

    prop_type = _get("property_type").lower() or None
    if prop_type and prop_type not in _VALID_PROPERTY_TYPES:
        warnings.append(f"property_type '{prop_type}' not recognised — kept as-is")

    raw_price = _get("raw_price") or None
    price_kind = _get("price_kind").lower() or None
    if price_kind and price_kind not in _VALID_PRICE_KINDS:
        warnings.append(f"price_kind '{price_kind}' not recognised — kept as-is")
    if raw_price and not price_kind:
        price_kind = "exact"
        warnings.append("price_kind not supplied — defaulted to 'exact'")

    status: str
    if errors:
        status = "error"
    elif warnings or formula_flags:
        status = "warning"
    else:
        status = "ok"

    return CsvPreviewRow(
        row_index=row_index,
        address_line=address_line or None,
        suburb=suburb or None,
        state=state or None,
        postcode=postcode,
        beds=beds_val,
        baths=baths_val,
        cars=cars_val,
        land_sqm=land_val,
        floor_sqm=floor_val,
        property_type=prop_type,
        raw_price=raw_price,
        price_kind=price_kind,
        notes=notes,
        errors=errors,
        warnings=warnings,
        formula_flags=formula_flags,
        skippable=bool(errors),
        status=status,  # type: ignore[arg-type]
    )


def parse_csv_bytes(file_bytes: bytes) -> tuple[list[dict[str, str]], list[str]]:
    """Parse raw CSV bytes.  Returns (rows, headers_found).  Raises ValueError on parse failure."""
    text = file_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers_found = [h.strip().lower() for h in (reader.fieldnames or [])]
    rows = []
    for row in reader:
        rows.append({k.strip().lower(): v for k, v in row.items()})
    return rows, headers_found


def preview_csv(
    file_bytes: bytes,
    journey_id: uuid.UUID,
    filename: str,
) -> CsvPreviewResponse:
    """Parse and validate a CSV file.  No database writes."""
    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"File too large ({len(file_bytes)} bytes). Maximum is {MAX_FILE_BYTES} bytes.")

    rows, headers_found = parse_csv_bytes(file_bytes)

    if len(rows) > MAX_ROWS:
        raise ValueError(f"File has {len(rows)} rows. Maximum is {MAX_ROWS} rows per import.")

    headers_missing = sorted(REQUIRED_HEADERS - set(headers_found))

    preview_row_objects: list[CsvPreviewRow] = []
    for i, raw in enumerate(rows):
        preview_row_objects.append(_validate_row(raw, i))

    valid_count = sum(1 for r in preview_row_objects if not r.skippable)
    warn_count = sum(1 for r in preview_row_objects if r.status == "warning" and not r.skippable)
    error_count = sum(1 for r in preview_row_objects if r.skippable)

    batch_key = _derive_batch_key(file_bytes, journey_id)

    return CsvPreviewResponse(
        batch_key=batch_key,
        filename=filename,
        total_rows=len(rows),
        valid_rows=valid_count,
        warning_rows=warn_count,
        error_rows=error_count,
        preview_rows=preview_row_objects[:10],
        headers_found=headers_found,
        headers_missing=headers_missing,
    )


def _row_to_intake_request(row: CsvPreviewRow) -> IntakeRequest | None:
    if row.skippable or not row.address_line or not row.suburb or not row.state:
        return None
    price: PriceIn | None = None
    if row.raw_price and row.price_kind:
        try:
            price = PriceIn(price_kind=row.price_kind, raw_price=row.raw_price)  # type: ignore[arg-type]
        except Exception:
            price = None

    return IntakeRequest(
        mode="structured_form",
        structured=StructuredPayload(
            address_line=row.address_line,
            suburb=row.suburb,
            state=row.state,
            postcode=row.postcode,
            facts=FactsIn(
                beds=row.beds,
                baths=row.baths,
                cars=row.cars,
                land_sqm=row.land_sqm,
                floor_sqm=row.floor_sqm,
                property_type=row.property_type,  # type: ignore[arg-type]
            ),
            price=price,
            notes=row.notes,
        ),
    )


async def import_csv_batch(
    db: AsyncSession,
    journey: Journey,
    actor_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    skip_row_indices: list[int],
) -> CsvBatchResult:
    """Process a full CSV import batch with idempotency."""
    from app.services.intake import process_intake  # local to avoid circular

    # Re-derive batch key from file content
    batch_key = _derive_batch_key(file_bytes, journey.id)

    # Idempotency: check if batch already processed
    existing = (
        await db.execute(
            select(CsvImportBatch).where(
                CsvImportBatch.workspace_id == journey.workspace_id,
                CsvImportBatch.batch_key == batch_key,
            )
        )
    ).scalar_one_or_none()

    if existing is not None and existing.state == "completed":
        await db.commit()
        return CsvBatchResult(
            batch_id=existing.id,
            batch_key=batch_key,
            filename=existing.filename,
            state="completed",
            total_rows=existing.row_count,
            created=existing.created_count,
            matched_existing=existing.matched_count,
            requires_review=existing.review_count,
            failed=existing.failed_count,
            skipped=existing.skipped_count,
            row_results=[],
        )

    rows, headers = parse_csv_bytes(file_bytes)
    all_rows = [_validate_row(raw, i) for i, raw in enumerate(rows)]

    # Create (or reuse pending) batch record
    batch = existing
    if batch is None:
        batch = CsvImportBatch(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            batch_key=batch_key,
            filename=filename,
            row_count=len(all_rows),
            state="processing",
        )
        db.add(batch)
        await db.flush()
    else:
        batch.state = "processing"
        await db.flush()

    counts: dict[str, int] = {
        "created": 0,
        "matched": 0,
        "review": 0,
        "failed": 0,
        "skipped": 0,
    }
    row_results: list[dict[str, Any]] = []

    for row in all_rows:
        result_entry: dict[str, Any] = {
            "row_index": row.row_index,
            "address": f"{row.address_line}, {row.suburb} {row.state}" if row.address_line else "(invalid)",
            "formula_flags": row.formula_flags,
        }

        if row.row_index in skip_row_indices:
            counts["skipped"] += 1
            result_entry["outcome"] = "skipped"
            row_results.append(result_entry)
            continue

        if row.skippable:
            counts["failed"] += 1
            result_entry["outcome"] = "failed"
            result_entry["errors"] = row.errors
            row_results.append(result_entry)
            continue

        intake_request = _row_to_intake_request(row)
        if intake_request is None:
            counts["failed"] += 1
            result_entry["outcome"] = "failed"
            row_results.append(result_entry)
            continue

        try:
            result = await process_intake(
                db, journey, actor_id, intake_request,
                batch_id=batch.id,
                intake_mechanism_override="csv_import",
            )
            if result.state == "completed":
                counts["created"] += 1
                result_entry["outcome"] = "created"
                result_entry["property_id"] = str(result.property_id)
            elif result.state == "duplicate":
                counts["matched"] += 1
                result_entry["outcome"] = "matched_existing"
                result_entry["existing_property_id"] = str(result.duplicate_property_id)
            elif result.state == "requires_review":
                counts["review"] += 1
                result_entry["outcome"] = "requires_review"
                result_entry["property_id"] = str(result.property_id)
                result_entry["review_reasons"] = result.review_reasons
            else:
                counts["failed"] += 1
                result_entry["outcome"] = "failed"
        except Exception as exc:
            counts["failed"] += 1
            result_entry["outcome"] = "failed"
            result_entry["error"] = str(exc)[:200]

        row_results.append(result_entry)

    # Update batch summary
    batch.created_count = counts["created"]
    batch.matched_count = counts["matched"]
    batch.review_count = counts["review"]
    batch.failed_count = counts["failed"]
    batch.skipped_count = counts["skipped"]
    batch.state = "completed" if counts["failed"] == 0 else "partial"
    batch.completed_at = now_utc()
    await db.flush()

    await db.commit()

    return CsvBatchResult(
        batch_id=batch.id,
        batch_key=batch_key,
        filename=filename,
        state=batch.state,
        total_rows=len(all_rows),
        created=counts["created"],
        matched_existing=counts["matched"],
        requires_review=counts["review"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        row_results=row_results,
    )


CSV_TEMPLATE_HEADERS = [
    "address_line", "suburb", "state", "postcode",
    "beds", "baths", "cars", "land_sqm", "floor_sqm",
    "property_type", "raw_price", "price_kind", "notes",
]

CSV_TEMPLATE_EXAMPLE_ROWS = [
    [
        "1 Example Street", "Subiaco", "WA", "6008",
        "4", "2", "2", "600", "220",
        "house", "Offers over $980,000", "offers_over", "Corner block",
    ],
    [
        "2/81 Baker Drive", "Nedlands", "WA", "6009",
        "3", "2", "1", "", "140",
        "unit", "$750,000", "exact", "",
    ],
    [
        "81A River Road", "Fremantle", "WA", "6160",
        "", "", "", "", "",
        "", "Auction", "auction", "Open for inspection Sat",
    ],
]


def generate_template_csv() -> bytes:
    """Generate the downloadable CSV template with example rows."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_TEMPLATE_HEADERS)
    writer.writerows(CSV_TEMPLATE_EXAMPLE_ROWS)
    return buf.getvalue().encode("utf-8")
