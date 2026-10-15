"""u1_campaign_configuration_isolation

Buyer-campaign boundary on journeys, versioned campaign configuration, campaign-scoped report
idempotency with an explicit legacy ownership mapping, per-campaign property identity and
campaign attribution on notification events. Additive: no existing row is moved, relabelled,
deleted or re-keyed; historical report run IDs and idempotency keys are preserved unchanged.

Revision ID: d4e1f7a2b9c3
Revises: c8d5e2f9a4b1
Create Date: 2026-10-15 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e1f7a2b9c3"
down_revision: str | None = "c8d5e2f9a4b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Journey becomes the explicit buyer-campaign boundary. Existing journeys are house campaigns.
    op.add_column("journeys", sa.Column("campaign_kind", sa.String(length=16), nullable=False, server_default="house"))
    op.add_column("journeys", sa.Column("campaign_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_check_constraint("ck_journey_campaign_kind", "journeys", "campaign_kind in ('house','land')")

    # Property identity is per campaign: the same address may exist independently in another campaign.
    # The new key is strictly weaker than the old one, so every existing row already satisfies it.
    op.drop_constraint("uq_property_workspace_address", "properties", type_="unique")
    op.create_unique_constraint(
        "uq_property_workspace_journey_address", "properties", ["workspace_id", "journey_id", "normalised_address"]
    )

    # Report idempotency becomes campaign-scoped. Existing rows keep their exact key and are marked legacy.
    op.add_column(
        "report_runs",
        sa.Column("idempotency_scope", sa.String(length=20), nullable=False, server_default="workspace_legacy"),
    )
    op.create_check_constraint(
        "ck_report_run_idempotency_scope", "report_runs", "idempotency_scope in ('workspace_legacy','campaign')"
    )
    # Re-upgrade after a downgrade: rows written by U1 code carry their own campaign-scoped key.
    op.execute(
        "UPDATE report_runs SET idempotency_scope = 'campaign' "
        "WHERE journey_id IS NOT NULL AND idempotency_key LIKE 'c1:' || journey_id::text || ':%'"
    )
    op.drop_constraint("uq_report_run_workspace_key", "report_runs", type_="unique")
    op.create_unique_constraint(
        "uq_report_run_workspace_journey_key", "report_runs", ["workspace_id", "journey_id", "idempotency_key"]
    )

    op.create_table(
        "report_run_legacy_mappings",
        sa.Column("report_run_id", sa.UUID(), sa.ForeignKey("report_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("journey_id", sa.UUID(), sa.ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("legacy_idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("mapping_basis", sa.String(length=60), nullable=False),
        sa.Column("migration_revision", sa.String(length=32), nullable=False),
        sa.Column("mapped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "journey_id", "legacy_idempotency_key", name="uq_report_legacy_mapping_scope_key"),
    )
    # Explicit ownership mapping: a legacy run maps only to the journey it already records, and only
    # when that journey belongs to the same workspace. Unattributable rows stay unmapped and untouched.
    op.execute(
        """
        INSERT INTO report_run_legacy_mappings
            (report_run_id, workspace_id, journey_id, legacy_idempotency_key, mapping_basis, migration_revision)
        SELECT r.id, r.workspace_id, r.journey_id, r.idempotency_key, 'recorded_journey_same_workspace', 'd4e1f7a2b9c3'
        FROM report_runs r
        JOIN journeys j ON j.id = r.journey_id AND j.workspace_id = r.workspace_id
        WHERE r.idempotency_scope = 'workspace_legacy'
        """
    )

    op.create_table(
        "campaign_config_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("journey_id", sa.UUID(), sa.ForeignKey("journeys.id", ondelete="CASCADE"), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.String(length=400), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("scope in ('user_default','campaign')", name="ck_campaign_config_scope"),
        sa.CheckConstraint(
            "(scope = 'user_default' AND user_id IS NOT NULL AND journey_id IS NULL) OR "
            "(scope = 'campaign' AND journey_id IS NOT NULL AND user_id IS NULL)",
            name="ck_campaign_config_owner",
        ),
        sa.CheckConstraint("version_no >= 1", name="ck_campaign_config_version_no"),
    )
    op.create_index(
        "uq_campaign_config_user_version", "campaign_config_versions", ["workspace_id", "user_id", "version_no"],
        unique=True, postgresql_where=sa.text("scope = 'user_default'"),
    )
    op.create_index(
        "uq_campaign_config_campaign_version", "campaign_config_versions", ["journey_id", "version_no"],
        unique=True, postgresql_where=sa.text("scope = 'campaign'"),
    )

    # Campaign attribution for notification events, derived only from same-workspace source rows.
    op.add_column("notification_events", sa.Column("journey_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_notification_events_journey_id", "notification_events", "journeys", ["journey_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_notification_events_workspace_journey", "notification_events", ["workspace_id", "journey_id"])
    for source_table, link_column in (
        ("report_runs", "report_run_id"),
        ("properties", "property_id"),
        ("property_tasks", "task_id"),
        ("intake_events", "source_event_id"),
    ):
        op.execute(
            f"""
            UPDATE notification_events n SET journey_id = s.journey_id
            FROM {source_table} s JOIN journeys j ON j.id = s.journey_id AND j.workspace_id = s.workspace_id
            WHERE n.{link_column} = s.id AND s.workspace_id = n.workspace_id AND n.journey_id IS NULL
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    shared = bind.execute(
        sa.text(
            "SELECT count(*) FROM (SELECT workspace_id, normalised_address FROM properties "
            "GROUP BY 1, 2 HAVING count(*) > 1) d"
        )
    ).scalar_one()
    if shared:
        raise RuntimeError(
            f"Downgrade blocked: {shared} address(es) exist in more than one campaign of a workspace. "
            "The pre-U1 schema cannot represent them. No data was changed."
        )
    clashing = bind.execute(
        sa.text(
            "SELECT count(*) FROM (SELECT workspace_id, idempotency_key FROM report_runs "
            "GROUP BY 1, 2 HAVING count(*) > 1) d"
        )
    ).scalar_one()
    if clashing:
        raise RuntimeError(f"Downgrade blocked: {clashing} report key(s) would collide. No data was changed.")

    op.drop_index("ix_notification_events_workspace_journey", table_name="notification_events")
    op.drop_constraint("fk_notification_events_journey_id", "notification_events", type_="foreignkey")
    op.drop_column("notification_events", "journey_id")

    op.drop_index("uq_campaign_config_campaign_version", table_name="campaign_config_versions")
    op.drop_index("uq_campaign_config_user_version", table_name="campaign_config_versions")
    op.drop_table("campaign_config_versions")
    op.drop_table("report_run_legacy_mappings")

    op.drop_constraint("uq_report_run_workspace_journey_key", "report_runs", type_="unique")
    op.create_unique_constraint("uq_report_run_workspace_key", "report_runs", ["workspace_id", "idempotency_key"])
    op.drop_constraint("ck_report_run_idempotency_scope", "report_runs", type_="check")
    op.drop_column("report_runs", "idempotency_scope")

    op.drop_constraint("uq_property_workspace_journey_address", "properties", type_="unique")
    op.create_unique_constraint("uq_property_workspace_address", "properties", ["workspace_id", "normalised_address"])

    op.drop_constraint("ck_journey_campaign_kind", "journeys", type_="check")
    op.drop_column("journeys", "campaign_enabled")
    op.drop_column("journeys", "campaign_kind")
