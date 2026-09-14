"""m5_1_allow_reminder_processing_job

Revision ID: f4a8c6d2e1b9
Revises: e9f3b2c1d7a4
Create Date: 2026-09-15 10:15:00.000000
"""
from collections.abc import Sequence

from alembic import op


revision: str = "f4a8c6d2e1b9"
down_revision: str | None = "e9f3b2c1d7a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_scheduled_job_kind", "scheduled_jobs", type_="check")
    op.create_check_constraint(
        "ck_scheduled_job_kind",
        "scheduled_jobs",
        "job_kind in ('brief_reevaluation', 'source_health_check', 'intake_processing', 'report_release', 'reminder_processing')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_scheduled_job_kind", "scheduled_jobs", type_="check")
    op.create_check_constraint(
        "ck_scheduled_job_kind",
        "scheduled_jobs",
        "job_kind in ('brief_reevaluation', 'source_health_check', 'intake_processing', 'report_release')",
    )