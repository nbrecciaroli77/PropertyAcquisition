"""u2_land_feasibility_fact_keys

Allows the LAND_FEASIBILITY_V1 evidence keys on facts. Additive: no existing row changes; house facts
and stored evaluations are untouched. Downgrade is fail-closed while any land evidence fact exists.

Revision ID: e7b2a9c4f1d6
Revises: d4e1f7a2b9c3
Create Date: 2026-10-16 09:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b2a9c4f1d6"
down_revision: str | None = "d4e1f7a2b9c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASE_KEYS = ("beds", "baths", "cars", "land_sqm", "floor_sqm", "property_type", "detached", "condition", "location_tier")
LAND_KEYS = (
    "land_subtype", "usable_sqm", "land_price_minor", "seller_ceiling", "drive_minutes", "availability",
    "dwelling_pathway", "shed_present", "title_covenants", "legal_access", "zoning_dwelling", "building_envelope",
    "bushfire", "flood_wetlands", "power", "water", "wastewater", "modular_feasibility",
)


def _check(keys: tuple[str, ...]) -> str:
    return "key in (" + ", ".join(f"'{k}'" for k in keys) + ")"


def upgrade() -> None:
    op.drop_constraint("ck_fact_key", "facts", type_="check")
    op.create_check_constraint("ck_fact_key", "facts", _check(BASE_KEYS + LAND_KEYS))


def downgrade() -> None:
    count = op.get_bind().execute(
        sa.text("select count(*) from facts where key = any(:keys)"), {"keys": list(LAND_KEYS)}
    ).scalar_one()
    if count:
        raise RuntimeError(
            f"Refusing downgrade: {count} land evidence fact(s) exist. No data was changed. "
            "Use the code-only rollback instead."
        )
    op.drop_constraint("ck_fact_key", "facts", type_="check")
    op.create_check_constraint("ck_fact_key", "facts", _check(BASE_KEYS))
