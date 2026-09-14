"""m4_1_manual_intake

Milestone 4.1 schema additions:
- enrichment_records: add subject_key column; replace 3-field UniqueConstraint with two
  partial unique indexes (one for NULL subject_key, one for NOT NULL).
- intake_events: extend state check to include requires_review; add intake_mechanism,
  parser_version, duplicate_property_id, review_reasons columns.

Revision ID: f3c9b21a5d8e
Revises: 2105faf7bef7
Create Date: 2026-09-14 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3c9b21a5d8e"
down_revision: str | None = "2105faf7bef7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── enrichment_records ───────────────────────────────────────────────────
    op.add_column(
        "enrichment_records",
        sa.Column("subject_key", sa.String(length=200), nullable=True),
    )
    # Replace the simple 3-field unique constraint with two partial unique indexes
    # so subject_key can discriminate multiple anchors per (property, kind, source).
    op.drop_constraint("uq_enrichment_property_kind_source", "enrichment_records", type_="unique")
    op.create_index(
        "uq_enrichment_no_subject",
        "enrichment_records",
        ["property_id", "kind", "source_label"],
        unique=True,
        postgresql_where=sa.text("subject_key IS NULL"),
    )
    op.create_index(
        "uq_enrichment_with_subject",
        "enrichment_records",
        ["property_id", "kind", "source_label", "subject_key"],
        unique=True,
        postgresql_where=sa.text("subject_key IS NOT NULL"),
    )

    # ── intake_events ────────────────────────────────────────────────────────
    # Extend state check to include requires_review
    op.drop_constraint("ck_intake_event_state", "intake_events", type_="check")
    op.create_check_constraint(
        "ck_intake_event_state",
        "intake_events",
        "state in ('pending', 'processing', 'completed', 'failed', 'duplicate', 'requires_review')",
    )
    # New columns
    op.add_column(
        "intake_events",
        sa.Column("intake_mechanism", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "intake_events",
        sa.Column("parser_version", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "intake_events",
        sa.Column("duplicate_property_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "intake_events",
        sa.Column(
            "review_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_intake_event_duplicate_property",
        "intake_events",
        "properties",
        ["duplicate_property_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_intake_event_mechanism",
        "intake_events",
        "intake_mechanism in ('structured_form', 'url_with_facts', 'pasted_text')",
    )


def downgrade() -> None:
    # ── intake_events ────────────────────────────────────────────────────────
    op.drop_constraint("ck_intake_event_mechanism", "intake_events", type_="check")
    op.drop_constraint(
        "fk_intake_event_duplicate_property", "intake_events", type_="foreignkey"
    )
    op.drop_column("intake_events", "review_reasons")
    op.drop_column("intake_events", "duplicate_property_id")
    op.drop_column("intake_events", "parser_version")
    op.drop_column("intake_events", "intake_mechanism")
    op.drop_constraint("ck_intake_event_state", "intake_events", type_="check")
    op.create_check_constraint(
        "ck_intake_event_state",
        "intake_events",
        "state in ('pending', 'processing', 'completed', 'failed', 'duplicate')",
    )

    # ── enrichment_records ───────────────────────────────────────────────────
    op.drop_index("uq_enrichment_with_subject", table_name="enrichment_records")
    op.drop_index("uq_enrichment_no_subject", table_name="enrichment_records")
    op.create_unique_constraint(
        "uq_enrichment_property_kind_source",
        "enrichment_records",
        ["property_id", "kind", "source_label"],
    )
    op.drop_column("enrichment_records", "subject_key")
