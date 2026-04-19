"""vehicle_trip

Revision ID: 5b73e9bc69d5
Revises: 04b3728a5cd6
Create Date: 2026-04-19 08:32:58.617660
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5b73e9bc69d5"
down_revision = "04b3728a5cd6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "trip",
        sa.Column(
            "vehicle_id",
            sa.BigInteger(),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "ended_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ended_at_utc >= started_at_utc",
            name="ck_trip_ended_at_gte_started_at",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_trip_vehicle_id_started_at_utc",
        "trip",
        ["vehicle_id", "started_at_utc"],
        unique=False,
    )

    op.create_index(
        "ix_trip_vehicle_id_ended_at_utc",
        "trip",
        ["vehicle_id", "ended_at_utc"],
        unique=False,
    )

    op.create_index(
        "ix_trip_vehicle_id_started_at_utc_ended_at_utc",
        "trip",
        ["vehicle_id", "started_at_utc", "ended_at_utc"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_trip_vehicle_id_started_at_utc_ended_at_utc", table_name="trip")
    op.drop_index("ix_trip_vehicle_id_started_at_utc", table_name="trip")
    op.drop_index("ix_trip_vehicle_id_ended_at_utc", table_name="trip")
    op.drop_table("trip")
