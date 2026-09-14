"""Schemas for M4.2 CSV import API."""
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CsvPreviewRow(BaseModel):
    row_index: int
    address_line: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    beds: int | None = None
    baths: int | None = None
    cars: int | None = None
    land_sqm: int | None = None
    floor_sqm: int | None = None
    property_type: str | None = None
    raw_price: str | None = None
    price_kind: str | None = None
    notes: str | None = None
    # Validation
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    formula_flags: list[str] = Field(default_factory=list)  # column names with formula-like values
    skippable: bool = False  # True if fatal error that prevents import
    status: Literal["ok", "warning", "error"] = "ok"


class CsvPreviewResponse(BaseModel):
    batch_key: str
    filename: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    preview_rows: list[CsvPreviewRow]  # first 10
    headers_found: list[str]
    headers_missing: list[str]


class CsvImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_key: str = Field(min_length=64, max_length=64)
    # rows to skip (row_index) - user can deselect rows before confirming
    skip_row_indices: list[int] = Field(default_factory=list)


class CsvBatchResult(BaseModel):
    batch_id: UUID
    batch_key: str
    filename: str
    state: str
    total_rows: int
    created: int
    matched_existing: int
    requires_review: int
    failed: int
    skipped: int
    row_results: list[dict[str, Any]]
