"""m5_1_notifications_tasks_reminders

Revision ID: e9f3b2c1d7a4
Revises: a8d2e3f4b5c6
Create Date: 2026-09-15 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e9f3b2c1d7a4"
down_revision: str | None = "a8d2e3f4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("property_tasks", "property_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("property_tasks", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("property_tasks", sa.Column("assignee_user_id", sa.UUID(), nullable=True))
    op.add_column("property_tasks", sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"))
    op.add_column("property_tasks", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("property_tasks", sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Australia/Perth"))
    op.add_column("property_tasks", sa.Column("reminder_offset_minutes", sa.Integer(), nullable=True))
    op.add_column("property_tasks", sa.Column("status", sa.String(length=16), nullable=False, server_default="open"))
    op.add_column("property_tasks", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_property_task_assignee", "property_tasks", "users", ["assignee_user_id"], ["id"], ondelete="SET NULL")
    op.create_check_constraint("ck_property_task_priority", "property_tasks", "priority in ('low','normal','high')")
    op.create_check_constraint("ck_property_task_status", "property_tasks", "status in ('open','completed')")
    op.create_index("ix_property_tasks_workspace_due", "property_tasks", ["workspace_id", "due_at"])

    op.create_table(
        "notification_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("event_fingerprint", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("safe_deep_link", sa.String(length=500), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("property_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("source_event_id", sa.UUID(), nullable=True),
        sa.Column("report_run_id", sa.UUID(), nullable=True),
        sa.Column("evidence_ref", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["property_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_event_id"], ["intake_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_run_id"], ["report_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "event_fingerprint", name="uq_notification_event_workspace_fingerprint"),
        sa.CheckConstraint("category in ('new_property','material_property_change','price_change','inspection_change','evidence_gap','duplicate_review','task_assigned','task_due_soon','task_overdue','reminder','source_processing_failure','digest_ready','weekly_report_ready','monthly_report_ready','critical_service')", name="ck_notification_event_category"),
        sa.CheckConstraint("priority in ('low','normal','high','critical')", name="ck_notification_event_priority"),
    )
    op.create_index("ix_notification_events_workspace_created", "notification_events", ["workspace_id", "created_at"])
    op.create_table(
        "recipient_notifications",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("notification_event_id", sa.UUID(), nullable=False), sa.Column("recipient_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True), sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notification_event_id"], ["notification_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("notification_event_id", "recipient_user_id", name="uq_recipient_notification_event_user"),
    )
    op.create_index("ix_recipient_notifications_inbox", "recipient_notifications", ["workspace_id", "recipient_user_id", "created_at"])
    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("recipient_notification_id", sa.UUID(), nullable=False), sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"), sa.Column("delivery_state", sa.String(length=16), nullable=False, server_default="delivered"),
        sa.Column("detail", sa.String(length=400), nullable=True), sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_notification_id"], ["recipient_notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("recipient_notification_id", "channel", "attempt_no", name="uq_notification_delivery_attempt"),
        sa.CheckConstraint("channel in ('in_app','email')", name="ck_notification_delivery_channel"),
        sa.CheckConstraint("delivery_state in ('pending','delivered','suppressed','failed')", name="ck_notification_delivery_state"),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("workspace_id", sa.UUID(), nullable=False), sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("scope_key", sa.String(length=80), nullable=False), sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column("requested_channel", sa.String(length=16), nullable=False, server_default="in_app"), sa.Column("effective_channel", sa.String(length=16), nullable=False, server_default="in_app"),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")), sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True), sa.Column("timezone", sa.String(length=64), nullable=True), sa.Column("due_soon_minutes", sa.Integer(), nullable=True),
        sa.Column("report_daily_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("report_weekly_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("report_monthly_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("workspace_id", "user_id", "scope_key", name="uq_notification_preference_scope"),
        sa.CheckConstraint("requested_channel in ('off','in_app','email','both')", name="ck_notification_pref_requested"), sa.CheckConstraint("effective_channel in ('off','in_app','email','both')", name="ck_notification_pref_effective"),
    )
    op.create_index("ix_notification_preferences_workspace_user", "notification_preferences", ["workspace_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_preferences_workspace_user", table_name="notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_table("notification_delivery_attempts")
    op.drop_index("ix_recipient_notifications_inbox", table_name="recipient_notifications")
    op.drop_table("recipient_notifications")
    op.drop_index("ix_notification_events_workspace_created", table_name="notification_events")
    op.drop_table("notification_events")
    op.drop_index("ix_property_tasks_workspace_due", table_name="property_tasks")
    op.drop_constraint("ck_property_task_status", "property_tasks", type_="check")
    op.drop_constraint("ck_property_task_priority", "property_tasks", type_="check")
    op.drop_constraint("fk_property_task_assignee", "property_tasks", type_="foreignkey")
    op.drop_column("property_tasks", "deleted_at")
    op.drop_column("property_tasks", "status")
    op.drop_column("property_tasks", "reminder_offset_minutes")
    op.drop_column("property_tasks", "timezone")
    op.drop_column("property_tasks", "due_at")
    op.drop_column("property_tasks", "priority")
    op.drop_column("property_tasks", "assignee_user_id")
    op.drop_column("property_tasks", "notes")
    op.alter_column("property_tasks", "property_id", existing_type=sa.UUID(), nullable=False)