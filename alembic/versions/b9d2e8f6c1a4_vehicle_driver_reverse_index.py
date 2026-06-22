"""vehicle driver reverse index

Revision ID: b9d2e8f6c1a4
Revises: a8c4f2d91b37
Create Date: 2026-06-18 00:00:00.000000
"""

from alembic import op

revision = "b9d2e8f6c1a4"
down_revision = "a8c4f2d91b37"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_vehicle_driver_assignment_driver_vehicle",
        "vehicle_driver_assignment",
        ["driver_id", "vehicle_id"],
    )


def downgrade():
    op.drop_index(
        "ix_vehicle_driver_assignment_driver_vehicle",
        table_name="vehicle_driver_assignment",
    )
