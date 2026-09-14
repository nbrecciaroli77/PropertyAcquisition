"""m4_2_csv_duplicate_review

Milestone 4.2 schema additions:
- properties: add merged_into_id, merged_at, merge_actor_user_id
- intake_events: extend intake_mechanism check to include csv_import; add batch_id FK
- New tables: csv_import_batches, duplicate_proposals

Revision ID: a8d2e3f4b5c6
Revises: f3c9b21a5d8e
Create Date: 2026-09-14 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8d2e3f4b5c6"
down_revision: str | None = "f3c9b21a5d8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── csv_import_batches (new table) ───────────────────────────────────────
    op.create_table(
        "csv_import_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("journey_id", sa.UUID(), nullable=False),
        sa.Column("batch_key", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=260), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("state", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journey_id"], ["journeys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "batch_key", name="uq_csv_batch_workspace_key"),
        sa.CheckConstraint(
            "state in ('pending', 'processing', 'completed', 'partial', 'failed')",
            name="ck_csv_batch_state",
        ),
    )
    op.create_index("ix_csv_batches_workspace_journey", "csv_import_batches", ["workspace_id", "journey_id"])

    # ── duplicate_proposals (new table) ──────────────────────────────────────
    op.create_table(
        "duplicate_proposals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("property_id_a", sa.UUID(), nullable=False),
        sa.Column("property_id_b", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("proposal_reason", sa.String(length=30), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("unit_suffix_warning", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("merge_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id_a"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id_b"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "state in ('pending', 'confirmed', 'rejected', 'undone')",
            name="ck_duplicate_proposal_state",
        ),
        sa.CheckConstraint(
            "proposal_reason in ('exact_address_intake', 'address_scan', 'user_proposed')",
            name="ck_duplicate_proposal_reason",
        ),
        sa.CheckConstraint("property_id_a <> property_id_b", name="ck_duplicate_no_self"),
    )
    op.create_index("ix_duplicate_proposals_workspace", "duplicate_proposals", ["workspace_id"])
    op.create_index(
        "ix_duplicate_proposals_pair",
        "duplicate_proposals",
        ["workspace_id", "property_id_a", "property_id_b"],
    )

    # ── properties: soft-merge columns ───────────────────────────────────────
    op.add_column("properties", sa.Column("merged_into_id", sa.UUID(), nullable=True))
    op.add_column("properties", sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("properties", sa.Column("merge_actor_user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_property_merged_into", "properties", "properties",
        ["merged_into_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_property_merge_actor", "properties", "users",
        ["merge_actor_user_id"], ["id"], ondelete="SET NULL",
    )

    # ── intake_events: extend intake_mechanism, add batch_id ─────────────────
    op.drop_constraint("ck_intake_event_mechanism", "intake_events", type_="check")
    op.create_check_constraint(
        "ck_intake_event_mechanism",
        "intake_events",
        "intake_mechanism in ('structured_form', 'url_with_facts', 'pasted_text', 'csv_import')",
    )
    op.add_column(
        "intake_events",
        sa.Column("batch_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_intake_event_batch", "intake_events", "csv_import_batches",
        ["batch_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    # ── intake_events ─────────────────────────────────────────────────────────
    op.drop_constraint("fk_intake_event_batch", "intake_events", type_="foreignkey")
    op.drop_column("intake_events", "batch_id")
    op.drop_constraint("ck_intake_event_mechanism", "intake_events", type_="check")
    op.create_check_constraint(
        "ck_intake_event_mechanism",
        "intake_events",
        "intake_mechanism in ('structured_form', 'url_with_facts', 'pasted_text')",
    )

    # ── properties ────────────────────────────────────────────────────────────
    op.drop_constraint("fk_property_merge_actor", "properties", type_="foreignkey")
    op.drop_constraint("fk_property_merged_into", "properties", type_="foreignkey")
    op.drop_column("properties", "merge_actor_user_id")
    op.drop_column("properties", "merged_at")
    op.drop_column("properties", "merged_into_id")

    # ── duplicate_proposals ───────────────────────────────────────────────────
    op.drop_index("ix_duplicate_proposals_pair", table_name="duplicate_proposals")
    op.drop_index("ix_duplicate_proposals_workspace", table_name="duplicate_proposals")
    op.drop_table("duplicate_proposals")

    # ── csv_import_batches ────────────────────────────────────────────────────
    op.drop_index("ix_csv_batches_workspace_journey", table_name="csv_import_batches")
    op.drop_table("csv_import_batches")
