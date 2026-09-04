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
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
