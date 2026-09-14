"""m6_1_product_alignment

Revision ID: c8d5e2f9a4b1
Revises: b7c4d1e8f2a3
Create Date: 2026-09-17 09:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c8d5e2f9a4b1"
down_revision: str | None = "b7c4d1e8f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rights and redistribution safety metadata on the connector catalog.
    op.add_column("connector_definitions", sa.Column("redistribution_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("connector_definitions", sa.Column("attribution_text", sa.Text(), nullable=True))

    # Producer/delivery separation: immutable READY_TO_SEND snapshot markers on report_runs.
    op.add_column("report_runs", sa.Column("ready_to_send_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("report_runs", sa.Column("ready_to_send_by", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_report_runs_ready_to_send_by", "report_runs", "users", ["ready_to_send_by"], ["id"], ondelete="SET NULL")
    op.drop_constraint("ck_report_run_release_state", "report_runs", type_="check")
    op.create_check_constraint(
        "ck_report_run_release_state", "report_runs",
        "release_state in ('pending','generating','ready','ready_to_send','failed','released')",
    )

    # Manual inspection feedback on buyer_properties.
    op.add_column("buyer_properties", sa.Column("inspection_state", sa.String(length=20), nullable=False, server_default="not_inspected"))
    op.add_column("buyer_properties", sa.Column("inspection_note", sa.Text(), nullable=True))
    op.add_column("buyer_properties", sa.Column("inspection_recorded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("buyer_properties", sa.Column("inspection_recorded_by", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_buyer_properties_inspection_recorded_by", "buyer_properties", "users", ["inspection_recorded_by"], ["id"], ondelete="SET NULL")
    op.create_check_constraint(
        "ck_buyer_property_inspection_state", "buyer_properties",
        "inspection_state in ('not_inspected','feedback_pending','great','ok','not_as_good')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_buyer_property_inspection_state", "buyer_properties", type_="check")
    op.drop_constraint("fk_buyer_properties_inspection_recorded_by", "buyer_properties", type_="foreignkey")
    op.drop_column("buyer_properties", "inspection_recorded_by")
    op.drop_column("buyer_properties", "inspection_recorded_at")
    op.drop_column("buyer_properties", "inspection_note")
    op.drop_column("buyer_properties", "inspection_state")

    op.drop_constraint("ck_report_run_release_state", "report_runs", type_="check")
    op.create_check_constraint(
        "ck_report_run_release_state", "report_runs",
        "release_state in ('pending','generating','ready','failed','released')",
    )
    op.drop_constraint("fk_report_runs_ready_to_send_by", "report_runs", type_="foreignkey")
    op.drop_column("report_runs", "ready_to_send_by")
    op.drop_column("report_runs", "ready_to_send_at")

    op.drop_column("connector_definitions", "attribution_text")
    op.drop_column("connector_definitions", "redistribution_allowed")
