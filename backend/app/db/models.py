"""Milestone 2 schema: accounts, tenancy, journeys and the versioned buying brief.

Every workspace-owned table carries `workspace_id` so tenant scoping is enforceable in the
database as well as the application layer. `workspace_id` is never accepted from the client.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Australia/Perth")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-AU")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Australia/Perth")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_membership_workspace_user"),
        CheckConstraint("role in ('owner','editor','viewer','support')", name="ck_membership_role"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="owner")


class AuthSession(Base):
    """Server-side revocable session. Access tokens carry `sid` and are checked against this row."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_agent: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(40))


class AuthToken(Base):
    """Single-use email verification and password reset tokens (hashes only)."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint("kind in ('verify_email','password_reset')", name="ck_auth_token_kind"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxMessage(Base):
    """Durable outbox. Delivery is suppressed: no provider is configured in this prototype."""

    __tablename__ = "outbox_messages"
    __table_args__ = (
        CheckConstraint(
            "delivery_state in ('suppressed_no_provider','queued','sent','failed')", name="ck_outbox_state"
        ),
        Index("ix_outbox_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    to_email: Mapped[str] = mapped_column(String(320), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(Text)
    dedupe_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    delivery_state: Mapped[str] = mapped_column(String(32), nullable=False, default="suppressed_no_provider")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_identifier_created", "identifier", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    identifier: Mapped[str] = mapped_column(String(400), nullable=False)
    successful: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Journey(Base, TimestampMixin):
    """A buying journey. Holds the resumable onboarding state and the working brief draft."""

    __tablename__ = "journeys"
    __table_args__ = (
        CheckConstraint("status in ('onboarding','active','archived')", name="ck_journey_status"),
        Index("ix_journeys_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="onboarding")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Australia/Perth")
    onboarding_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    draft_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    draft_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brief_versions.id", ondelete="SET NULL", use_alter=True)
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


class BriefVersion(Base):
    """Immutable published brief. Never updated after insert."""

    __tablename__ = "brief_versions"
    __table_args__ = (UniqueConstraint("journey_id", "version_no", name="uq_brief_version_no"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(String(400), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reevaluation_state: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")


MARKET_STATES = ("active", "under_offer", "withdrawn", "sold", "unknown")
PRICE_KINDS = (
    "exact",
    "range",
    "from",
    "offers_over",
    "auction",
    "contact_agent",
    "expressions_of_interest",
    "conflicting",
)
BUYER_STATES = (
    "reviewing",
    "shortlisted",
    "inspection_considered",
    "inspected",
    "due_diligence",
    "offer_preparation",
    "offer_submitted",
    "under_contract",
    "settled",
    "rejected",
    "archived",
)
FACT_KEYS = (
    "beds",
    "baths",
    "cars",
    "land_sqm",
    "floor_sqm",
    "property_type",
    "detached",
    "condition",
    "location_tier",
)
VALUE_STATES = ("known", "unknown", "not_applicable", "conflict")
SOURCE_KINDS = ("original_source", "partial", "manual", "conflict")


class Property(Base, TimestampMixin):
    """Physical address identity. Unit suffixes are part of identity: 81A and 81C never merge."""

    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("workspace_id", "normalised_address", name="uq_property_workspace_address"),
        Index("ix_properties_workspace_journey", "workspace_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    legacy_ref: Mapped[str | None] = mapped_column(String(40))
    address_line: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    suburb: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(3), nullable=False)
    postcode: Mapped[str | None] = mapped_column(String(4))
    normalised_address: Mapped[str] = mapped_column(String(320), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    image_attribution: Mapped[str | None] = mapped_column(String(200))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    # Soft-merge support: set when this property is absorbed into another
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL")
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merge_actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class ListingCampaign(Base, TimestampMixin):
    """Provider-specific sale campaign. Market state lives here, never on the buyer record."""

    __tablename__ = "listing_campaigns"
    __table_args__ = (
        CheckConstraint(f"market_state in {MARKET_STATES!r}", name="ck_campaign_market_state"),
        CheckConstraint(f"price_kind in {PRICE_KINDS!r}", name="ck_campaign_price_kind"),
        Index("ix_campaigns_property", "property_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    source_label: Mapped[str] = mapped_column(String(120), nullable=False)
    market_state: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    price_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_price: Mapped[str] = mapped_column(String(120), nullable=False)
    lower_minor: Mapped[int | None] = mapped_column(Integer)
    upper_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")
    price_source: Mapped[str] = mapped_column(String(120), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Observation(Base):
    """One look at one source at one time. Facts point back here for provenance."""

    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint(f"source_kind in {SOURCE_KINDS!r}", name="ck_observation_source_kind"),
        Index("ix_observations_property", "property_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    source_label: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class Fact(Base, TimestampMixin):
    """A material fact with provenance. `value_state` keeps unknown, not-applicable and conflict distinct."""

    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint("property_id", "key", name="uq_fact_property_key"),
        CheckConstraint(f"key in {FACT_KEYS!r}", name="ck_fact_key"),
        CheckConstraint(f"value_state in {VALUE_STATES!r}", name="ck_fact_value_state"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    value_state: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    value_int: Mapped[int | None] = mapped_column(Integer)
    value_text: Mapped[str | None] = mapped_column(String(80))
    value_bool: Mapped[bool | None] = mapped_column(Boolean)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="stated")
    conflict_note: Mapped[str | None] = mapped_column(Text)


class BuyerProperty(Base, TimestampMixin):
    """Household workflow state for a property inside one journey. Separate from market state."""

    __tablename__ = "buyer_properties"
    __table_args__ = (
        UniqueConstraint("journey_id", "property_id", name="uq_buyer_property_journey"),
        CheckConstraint(f"buyer_state in {BUYER_STATES!r}", name="ck_buyer_state"),
        Index("ix_buyer_properties_workspace_journey", "workspace_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    buyer_state: Mapped[str] = mapped_column(String(24), nullable=False, default="reviewing")
    saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stage_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage_changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class MatchEvaluation(Base):
    """Deterministic evaluation of one property against one immutable brief version."""

    __tablename__ = "match_evaluations"
    __table_args__ = (
        UniqueConstraint("property_id", "brief_version_id", name="uq_evaluation_property_version"),
        CheckConstraint("verdict in ('pass','fail','unknown')", name="ck_evaluation_verdict"),
        Index("ix_evaluations_journey_version", "journey_id", "brief_version_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    brief_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brief_versions.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    verdict: Mapped[str] = mapped_column(String(8), nullable=False)
    fit_pct: Mapped[int | None] = mapped_column(Integer)
    coverage_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GateWaiver(Base):
    """Property-specific, reasoned acknowledgement of a Fail or Unknown gate. Never mutates the brief."""

    __tablename__ = "gate_waivers"
    __table_args__ = (Index("ix_waivers_property", "property_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    criterion: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(400), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PropertyNote(Base, TimestampMixin):
    __tablename__ = "property_notes"
    __table_args__ = (Index("ix_notes_property", "property_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class PropertyTask(Base, TimestampMixin):
    """Simple task. Due dates, ownership and reminders arrive in Milestone 5."""

    __tablename__ = "property_tasks"
    __table_args__ = (Index("ix_tasks_property", "property_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Australia/Perth")
    reminder_offset_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (Index("ix_activity_journey_created", "journey_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(String(400), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── M3A Foundation Alignment ───────────────────────────────────────────────────
# Provider-neutral connector catalog, source readiness, sender-alias review,
# discovery/intake attribution, scheduler observability, enrichment records and
# report-run metadata.  No external integrations are activated.

ACQUISITION_MECHANISMS = ("portal_api", "portal_scrape", "direct_api", "manual", "inbound_email")
LICENCE_KINDS = ("none_required", "commercial", "licensed")
LICENCE_STATES = ("not_required", "pending", "active", "suspended", "expired")
CONNECTOR_READINESS_STATES = ("unconfigured", "ready", "degraded", "error", "kill_switch")
SOURCE_READINESS_STATES = ("initialising", "ready", "degraded", "offline", "kill_switch")
ALIAS_CONFIDENCES = ("verified", "high", "medium", "low")
ALIAS_REVIEW_STATES = ("pending", "confirmed", "rejected")
DISCOVERY_EVENT_TYPES = ("first_discovery", "channel_event")
DISCOVERY_CHANNELS = ("portal", "email", "manual", "agent_referral", "direct")
INTAKE_STATES = ("pending", "processing", "completed", "failed", "duplicate", "requires_review")
INTAKE_MECHANISMS = ("structured_form", "url_with_facts", "pasted_text", "csv_import")
CSV_BATCH_STATES = ("pending", "processing", "completed", "partial", "failed")
DUPLICATE_PROPOSAL_STATES = ("pending", "confirmed", "rejected", "undone")
DUPLICATE_PROPOSAL_REASONS = ("exact_address_intake", "address_scan", "user_proposed")
JOB_KINDS = ("brief_reevaluation", "source_health_check", "intake_processing", "report_release", "reminder_processing")
JOB_RUN_STATES = ("running", "completed", "failed", "skipped")
ENRICHMENT_KINDS = ("planning", "constraint_layer", "notable_place", "travel")
ENRICHMENT_CONFIDENCES = ("stated", "derived", "estimated", "unknown")
REPORT_RUN_KINDS = ("preview", "on_demand", "production")
REPORT_RELEASE_STATES = ("pending", "generating", "ready", "failed", "released")


class ConnectorDefinition(Base, TimestampMixin):
    """Global, system-managed provider catalog.  No workspace_id — workspaces activate
    through ConnectorInstance only.  Workspace behaviour is never customised here."""

    __tablename__ = "connector_definitions"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_connector_definition_slug"),
        CheckConstraint(
            f"acquisition_mechanism in {ACQUISITION_MECHANISMS!r}",
            name="ck_connector_acquisition_mechanism",
        ),
        CheckConstraint(f"licence_kind in {LICENCE_KINDS!r}", name="ck_connector_licence_kind"),
        CheckConstraint(f"licence_state in {LICENCE_STATES!r}", name="ck_connector_licence_state"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    acquisition_mechanism: Mapped[str] = mapped_column(String(24), nullable=False)
    capabilities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    jurisdiction_codes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    licence_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    licence_state: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ConnectorInstance(Base, TimestampMixin):
    """Workspace-scoped activation of a ConnectorDefinition.
    credential_ref is a reference key only — raw credentials are never stored here."""

    __tablename__ = "connector_instances"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "definition_id", name="uq_connector_instance_workspace_definition"
        ),
        CheckConstraint(
            f"readiness_state in {CONNECTOR_READINESS_STATES!r}",
            name="ck_connector_instance_readiness_state",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    credential_ref: Mapped[str | None] = mapped_column(String(200))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    readiness_state: Mapped[str] = mapped_column(String(16), nullable=False, default="unconfigured")
    health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_detail: Mapped[str | None] = mapped_column(String(400))


class SourceReadiness(Base, TimestampMixin):
    """Service/source readiness per workspace-connector pair, separated from the
    buyer's journey.  Tracks requested vs effective filters and deviation reason."""

    __tablename__ = "source_readiness"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "connector_instance_id", name="uq_source_readiness_workspace_connector"
        ),
        CheckConstraint(
            f"readiness_state in {SOURCE_READINESS_STATES!r}",
            name="ck_source_readiness_state",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    connector_instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_instances.id", ondelete="CASCADE"), nullable=False
    )
    readiness_state: Mapped[str] = mapped_column(String(16), nullable=False, default="initialising")
    milestones: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    requested_filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    effective_filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    deviation_reason: Mapped[str | None] = mapped_column(String(400))
    status_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SenderAlias(Base, TimestampMixin):
    """Verified sender-alias review.  Primary contact (canonical_email) remains
    separate from aliases.  display_names_seen is stored for reference only and
    is never used as a matching key."""

    __tablename__ = "sender_aliases"
    __table_args__ = (
        UniqueConstraint("workspace_id", "alias_email", name="uq_sender_alias_workspace_email"),
        CheckConstraint(f"confidence in {ALIAS_CONFIDENCES!r}", name="ck_sender_alias_confidence"),
        CheckConstraint(f"review_state in {ALIAS_REVIEW_STATES!r}", name="ck_sender_alias_review_state"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    canonical_email: Mapped[str] = mapped_column(String(320), nullable=False)
    alias_email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_names_seen: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_label: Mapped[str] = mapped_column(String(200), nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    review_state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class DiscoveryEvent(Base):
    """Discovery and ingestion attribution.  event_type='first_discovery' records the
    first time a property was found; a partial unique index enforces exactly one
    first_discovery per (workspace_id, property_id).  Subsequent channel events use
    event_type='channel_event' and are stored in the same table without the uniqueness
    constraint."""

    __tablename__ = "discovery_events"
    __table_args__ = (
        CheckConstraint(f"event_type in {DISCOVERY_EVENT_TYPES!r}", name="ck_discovery_event_type"),
        CheckConstraint(f"channel in {DISCOVERY_CHANNELS!r}", name="ck_discovery_channel"),
        Index("ix_discovery_workspace_property", "workspace_id", "property_id"),
        # Exactly one first_discovery per (workspace, property)
        Index(
            "uq_discovery_first_per_workspace_property",
            "workspace_id",
            "property_id",
            unique=True,
            postgresql_where=text("event_type = 'first_discovery'"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, default="first_discovery")
    source_label: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    claim: Mapped[str | None] = mapped_column(String(200))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IntakeEvent(Base):
    """Durable, idempotent intake-processing record.  Prompt 04 reads and writes these.
    idempotency_key is unique per workspace (not globally) so different workspaces may
    derive identical keys from the same external source without colliding."""

    __tablename__ = "intake_events"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_intake_event_workspace_key"
        ),
        CheckConstraint(f"channel in {DISCOVERY_CHANNELS!r}", name="ck_intake_event_channel"),
        CheckConstraint(f"state in {INTAKE_STATES!r}", name="ck_intake_event_state"),
        CheckConstraint(
            f"intake_mechanism in {INTAKE_MECHANISMS!r}",
            name="ck_intake_event_mechanism",
        ),
        Index("ix_intake_events_workspace_journey", "workspace_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source_label: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    intake_mechanism: Mapped[str | None] = mapped_column(String(24))
    parser_version: Mapped[str | None] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_property_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL")
    )
    duplicate_property_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL")
    )
    review_reasons: Mapped[list[Any] | None] = mapped_column(JSONB)
    error_detail: Mapped[str | None] = mapped_column(Text)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("csv_import_batches.id", ondelete="SET NULL")
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CsvImportBatch(Base, TimestampMixin):
    """Tracks a CSV file import.  batch_key ensures the same file+journey combination is
    idempotent — replaying the identical file does not duplicate properties."""

    __tablename__ = "csv_import_batches"
    __table_args__ = (
        UniqueConstraint("workspace_id", "batch_key", name="uq_csv_batch_workspace_key"),
        CheckConstraint(f"state in {CSV_BATCH_STATES!r}", name="ck_csv_batch_state"),
        Index("ix_csv_batches_workspace_journey", "workspace_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False
    )
    batch_key: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DuplicateProposal(Base, TimestampMixin):
    """Workspace-scoped duplicate candidate.  Never auto-merged.  All confirm/reject/undo
    actions are audited.  property_id_a is the default primary (survivor); the user may
    swap before confirming.  merge_snapshot stores moved record IDs for safe undo."""

    __tablename__ = "duplicate_proposals"
    __table_args__ = (
        CheckConstraint(
            f"state in {DUPLICATE_PROPOSAL_STATES!r}", name="ck_duplicate_proposal_state"
        ),
        CheckConstraint(
            f"proposal_reason in {DUPLICATE_PROPOSAL_REASONS!r}",
            name="ck_duplicate_proposal_reason",
        ),
        CheckConstraint("property_id_a <> property_id_b", name="ck_duplicate_no_self"),
        Index("ix_duplicate_proposals_workspace", "workspace_id"),
        Index(
            "ix_duplicate_proposals_pair", "workspace_id", "property_id_a", "property_id_b"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    property_id_a: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )
    property_id_b: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    proposal_reason: Mapped[str] = mapped_column(String(30), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    unit_suffix_warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    merge_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    review_reason: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)



class ScheduledJob(Base, TimestampMixin):
    """Scheduler configuration record.  workspace_id is required for this prototype —
    no system-wide nullable tenancy path.  enabled defaults to False; no scheduler
    or background automation is activated by this migration."""

    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        CheckConstraint(f"job_kind in {JOB_KINDS!r}", name="ck_scheduled_job_kind"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    job_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    schedule_cron: Mapped[str] = mapped_column(String(80), nullable=False)
    schedule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobRun(Base):
    """Individual job-execution observability record.  No scheduler is activated;
    these rows would be written by the job runner when it exists."""

    __tablename__ = "job_runs"
    __table_args__ = (
        CheckConstraint(f"run_state in {JOB_RUN_STATES!r}", name="ck_job_run_state"),
        Index("ix_job_runs_job_started", "job_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheduled_jobs.id", ondelete="CASCADE"), nullable=False
    )
    run_state: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(400))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnrichmentRecord(Base, TimestampMixin):
    """Provider-neutral enrichment for planning, constraint layers, notable places and
    travel.  Reuses VALUE_STATES for value_state.  subject_key discriminates between
    multiple anchors of the same kind+source (e.g. travel time to different destinations).
    Two partial unique indexes enforce uniqueness: one for rows where subject_key IS NULL
    (3-field key, backward-compatible) and one for rows where it IS NOT NULL (4-field key)."""

    __tablename__ = "enrichment_records"
    __table_args__ = (
        CheckConstraint(f"kind in {ENRICHMENT_KINDS!r}", name="ck_enrichment_kind"),
        CheckConstraint(
            f"confidence in {ENRICHMENT_CONFIDENCES!r}", name="ck_enrichment_confidence"
        ),
        CheckConstraint(f"value_state in {VALUE_STATES!r}", name="ck_enrichment_value_state"),
        Index("ix_enrichment_property", "property_id"),
        # Partial unique indexes replacing the simple 3-field UniqueConstraint from M3A.
        # Managed by the M4.1 migration; the model-level Index entries are informational only.
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source_label: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_key: Mapped[str | None] = mapped_column(String(200))
    provenance: Mapped[str] = mapped_column(String(400), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    freshness_days: Mapped[int | None] = mapped_column(Integer)
    value_state: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ReportRun(Base, TimestampMixin):
    """Report-run/release metadata.  Distinguishes preview, on-demand and future
    production releases.  idempotency_key is unique per workspace.  No email
    delivery is performed."""

    __tablename__ = "report_runs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_report_run_workspace_key"),
        CheckConstraint(f"kind in {REPORT_RUN_KINDS!r}", name="ck_report_run_kind"),
        CheckConstraint(
            f"release_state in {REPORT_RELEASE_STATES!r}", name="ck_report_run_release_state"
        ),
        Index("ix_report_runs_workspace_journey", "workspace_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journeys.id", ondelete="SET NULL")
    )
    brief_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brief_versions.id", ondelete="SET NULL")
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="preview")
    release_state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


# ── M5.1 Notifications, tasks and reminders ──────────────────────────────────
NOTIFICATION_CATEGORIES = (
    "new_property",
    "material_property_change",
    "price_change",
    "inspection_change",
    "evidence_gap",
    "duplicate_review",
    "task_assigned",
    "task_due_soon",
    "task_overdue",
    "reminder",
    "source_processing_failure",
    "digest_ready",
    "weekly_report_ready",
    "monthly_report_ready",
    "critical_service",
)
NOTIFICATION_PRIORITIES = ("low", "normal", "high", "critical")
NOTIFICATION_CHANNELS = ("off", "in_app", "email", "both")
DELIVERY_CHANNELS = ("in_app", "email")
DELIVERY_STATES = ("pending", "delivered", "suppressed", "failed")
TASK_PRIORITIES = ("low", "normal", "high")
TASK_STATUSES = ("open", "completed")


class NotificationEvent(Base, TimestampMixin):
    """Deterministic workspace event. Its fingerprint is the idempotency boundary."""

    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint("workspace_id", "event_fingerprint", name="uq_notification_event_workspace_fingerprint"),
        CheckConstraint(f"category in {NOTIFICATION_CATEGORIES!r}", name="ck_notification_event_category"),
        CheckConstraint(f"priority in {NOTIFICATION_PRIORITIES!r}", name="ck_notification_event_priority"),
        Index("ix_notification_events_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    event_fingerprint: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    safe_deep_link: Mapped[str] = mapped_column(String(500), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property_tasks.id", ondelete="SET NULL"))
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("intake_events.id", ondelete="SET NULL"))
    report_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_runs.id", ondelete="SET NULL"))
    evidence_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecipientNotification(Base):
    """A recipient's durable inbox state; events are never shared as read/dismissed state."""

    __tablename__ = "recipient_notifications"
    __table_args__ = (
        UniqueConstraint("notification_event_id", "recipient_user_id", name="uq_recipient_notification_event_user"),
        Index("ix_recipient_notifications_inbox", "workspace_id", "recipient_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    notification_event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notification_events.id", ondelete="CASCADE"), nullable=False)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationDeliveryAttempt(Base):
    """Channel delivery audit. Email rows are never created while no provider is connected."""

    __tablename__ = "notification_delivery_attempts"
    __table_args__ = (
        UniqueConstraint("recipient_notification_id", "channel", "attempt_no", name="uq_notification_delivery_attempt"),
        CheckConstraint(f"channel in {DELIVERY_CHANNELS!r}", name="ck_notification_delivery_channel"),
        CheckConstraint(f"delivery_state in {DELIVERY_STATES!r}", name="ck_notification_delivery_state"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    recipient_notification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipient_notifications.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivery_state: Mapped[str] = mapped_column(String(16), nullable=False, default="delivered")
    detail: Mapped[str | None] = mapped_column(String(400))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NotificationPreference(Base, TimestampMixin):
    """Requested and effective channel values stay separate for future provider activation."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", "scope_key", name="uq_notification_preference_scope"),
        CheckConstraint(f"requested_channel in {NOTIFICATION_CHANNELS!r}", name="ck_notification_pref_requested"),
        CheckConstraint(f"effective_channel in {NOTIFICATION_CHANNELS!r}", name="ck_notification_pref_effective"),
        Index("ix_notification_preferences_workspace_user", "workspace_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str | None] = mapped_column(String(40))
    requested_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="in_app")
    effective_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="in_app")
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5))
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5))
    timezone: Mapped[str | None] = mapped_column(String(64))
    due_soon_minutes: Mapped[int | None] = mapped_column(Integer)
    report_daily_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_weekly_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_monthly_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
