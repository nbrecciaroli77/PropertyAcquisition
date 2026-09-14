"""Pydantic schemas for the M4.1 manual property intake API.

All workspace_id derivation happens server-side from the authenticated session.
journey_id is taken from the URL path only — never from the request body.
"""
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Sub-objects ──────────────────────────────────────────────────────────────


class FactsIn(Strict):
    """Optional property facts supplied by the user.  Omitted fields stay Unknown."""

    beds: int | None = Field(default=None, ge=0, le=30)
    baths: int | None = Field(default=None, ge=0, le=20)
    cars: int | None = Field(default=None, ge=0, le=20)
    land_sqm: int | None = Field(default=None, ge=1)
    floor_sqm: int | None = Field(default=None, ge=1)
    property_type: Literal[
        "house", "townhouse", "villa", "unit", "apartment", "land", "acreage"
    ] | None = None
    detached: bool | None = None
    condition: Literal["move_in_ready", "usable_home", "renovation"] | None = None
    location_tier: Literal["primary", "strong_alternative", "conditional"] | None = None


class PriceIn(Strict):
    price_kind: Literal[
        "exact",
        "range",
        "from",
        "offers_over",
        "auction",
        "contact_agent",
        "expressions_of_interest",
        "conflicting",
    ]
    raw_price: str = Field(min_length=1, max_length=120)
    lower_minor: int | None = Field(default=None, ge=0)  # cents
    upper_minor: int | None = Field(default=None, ge=0)  # cents


# ── Mode payloads ────────────────────────────────────────────────────────────


class StructuredPayload(Strict):
    address_line: str = Field(min_length=2, max_length=200)
    suburb: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=2, max_length=3)
    postcode: str | None = Field(default=None, max_length=4)
    facts: FactsIn = Field(default_factory=FactsIn)
    price: PriceIn | None = None
    notes: str | None = Field(default=None, max_length=2000)


class UrlWithFactsPayload(Strict):
    """URL stored as attribution reference only.  Never fetched or scraped."""

    source_url: str = Field(min_length=1, max_length=2000)
    address_line: str = Field(min_length=2, max_length=200)
    suburb: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=2, max_length=3)
    postcode: str | None = Field(default=None, max_length=4)
    facts: FactsIn = Field(default_factory=FactsIn)
    price: PriceIn | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PastedTextPayload(Strict):
    raw_text: str = Field(min_length=1, max_length=10000)
    # User-supplied overrides/corrections applied on top of the parser's output.
    overrides: FactsIn = Field(default_factory=FactsIn)
    price_override: PriceIn | None = None
    notes: str | None = Field(default=None, max_length=2000)


# ── Top-level request ────────────────────────────────────────────────────────


class IntakeRequest(Strict):
    mode: Literal["structured_form", "url_with_facts", "pasted_text"]
    structured: StructuredPayload | None = None
    url_with_facts: UrlWithFactsPayload | None = None
    pasted_text: PastedTextPayload | None = None


# ── Responses ────────────────────────────────────────────────────────────────


class ParsedFactsOut(BaseModel):
    """What the text parser extracted.  Included in the parse-preview and intake responses."""

    address_line: str | None
    suburb: str | None
    state: str | None
    postcode: str | None
    beds: int | None
    baths: int | None
    cars: int | None
    land_sqm: int | None
    floor_sqm: int | None
    property_type: str | None
    price_kind: str | None
    raw_price: str | None
    lower_minor: int | None
    upper_minor: int | None
    review_reasons: list[str]
    parser_version: str


class IntakeResult(BaseModel):
    intake_id: UUID
    state: Literal["completed", "duplicate", "requires_review", "failed"]
    property_id: UUID | None = None           # set when state ∈ {completed, requires_review}
    duplicate_property_id: UUID | None = None  # set when state = duplicate
    duplicate_address: str | None = None       # human-readable for the duplicate
    review_reasons: list[str]
    parsed_facts: ParsedFactsOut | None = None  # included for pasted_text mode
    journey_id: UUID
