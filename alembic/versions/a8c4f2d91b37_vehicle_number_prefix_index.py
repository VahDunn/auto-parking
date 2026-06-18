"""vehicle number prefix index

Revision ID: a8c4f2d91b37
Revises: f6a8f0c9b2d1
Create Date: 2026-06-18 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "a8c4f2d91b37"
down_revision = "f6a8f0c9b2d1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("UPDATE vehicle SET vehicle_number = upper(trim(vehicle_number))"))
    op.create_index(
        "ix_vehicle_vehicle_number_prefix",
        "vehicle",
        ["vehicle_number"],
        postgresql_ops={"vehicle_number": "text_pattern_ops"},
    )


def downgrade():
    op.drop_index("ix_vehicle_vehicle_number_prefix", table_name="vehicle")
