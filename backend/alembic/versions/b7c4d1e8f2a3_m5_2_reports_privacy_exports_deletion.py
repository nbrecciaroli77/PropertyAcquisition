"""m5_2_reports_privacy_exports_deletion

Revision ID: b7c4d1e8f2a3
Revises: f4a8c6d2e1b9
Create Date: 2026-09-16 09:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b7c4d1e8f2a3"
down_revision: str | None = "f4a8c6d2e1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("report_runs", sa.Column("report_type", sa.String(length=16), nullable=False, server_default="daily"))
    op.add_column("report_runs", sa.Column("period_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("report_runs", sa.Column("period_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("report_runs", sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("report_runs", sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Australia/Perth"))
    op.add_column("report_runs", sa.Column("generation_version", sa.String(length=40), nullable=False, server_default="v1"))
    op.add_column("report_runs", sa.Column("is_partial_period", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("report_runs", sa.Column("failure_reason", sa.String(length=400), nullable=True))
    op.add_column("report_runs", sa.Column("snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")))
    op.create_check_constraint("ck_report_run_report_type", "report_runs", "report_type in ('daily','weekly','monthly')")

    op.create_table(
        "report_preferences",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("workspace_id", sa.UUID(), nullable=False), sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("report_type", sa.String(length=16), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("local_time", sa.String(length=5), nullable=False, server_default="07:00"),
        sa.Column("weekdays", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("day_of_week", sa.Integer(), nullable=True), sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Australia/Perth"),
        sa.Column("requested_channel", sa.String(length=16), nullable=False, server_default="in_app"),
        sa.Column("effective_channel", sa.String(length=16), nullable=False, server_default="in_app"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", "report_type", name="uq_report_preference_scope"),
        sa.CheckConstraint("report_type in ('daily','weekly','monthly')", name="ck_report_preference_type"),
        sa.CheckConstraint("requested_channel in ('off','in_app','email','both')", name="ck_report_preference_requested"),
        sa.CheckConstraint("effective_channel in ('off','in_app','email','both')", name="ck_report_preference_effective"),
    )

    op.create_table(
        "data_exports",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False), sa.Column("export_type", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("manifest", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("file_data", sa.LargeBinary(), nullable=True), sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.String(length=400), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True), sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("export_type in ('personal','workspace')", name="ck_data_export_type"),
        sa.CheckConstraint("state in ('pending','generating','ready','failed','expired')", name="ck_data_export_state"),
    )
    op.create_index("ix_data_exports_requested_by", "data_exports", ["requested_by_user_id", "created_at"])

    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("request_type", sa.String(length=24), nullable=False), sa.Column("target_workspace_id", sa.UUID(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="pending_cooloff"),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("scheduled_execute_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("request_type in ('leave_workspace','delete_account','delete_workspace')", name="ck_deletion_request_type"),
        sa.CheckConstraint("state in ('pending_cooloff','cancelled','processing','completed','failed')", name="ck_deletion_request_state"),
    )
    op.create_index("ix_deletion_requests_requested_by", "deletion_requests", ["requested_by_user_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_deletion_requests_requested_by", table_name="deletion_requests")
    op.drop_table("deletion_requests")
    op.drop_index("ix_data_exports_requested_by", table_name="data_exports")
    op.drop_table("data_exports")
    op.drop_table("report_preferences")
    op.drop_constraint("ck_report_run_report_type", "report_runs", type_="check")
    op.drop_column("report_runs", "snapshot")
    op.drop_column("report_runs", "failure_reason")
    op.drop_column("report_runs", "is_partial_period")
    op.drop_column("report_runs", "generation_version")
    op.drop_column("report_runs", "timezone")
    op.drop_column("report_runs", "cutoff_at")
    op.drop_column("report_runs", "period_end")
    op.drop_column("report_runs", "period_start")
    op.drop_column("report_runs", "report_type")
