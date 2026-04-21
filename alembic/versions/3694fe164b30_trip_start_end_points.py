"""trip_start_end_points

Revision ID: 3694fe164b30
Revises: 5b73e9bc69d5
Create Date: 2026-04-21 10:11:34.299147

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3694fe164b30"
down_revision = "5b73e9bc69d5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM trip")

    op.add_column(
        "trip",
        sa.Column("start_point_id", sa.BigInteger(), nullable=False),
    )
    op.add_column(
        "trip",
        sa.Column("end_point_id", sa.BigInteger(), nullable=False),
    )

    op.drop_index("ix_trip_vehicle_id_ended_at_utc", table_name="trip")
    op.drop_index("ix_trip_vehicle_id_started_at_utc", table_name="trip")

    op.create_index("ix_trip_start_point_id", "trip", ["start_point_id"], unique=False)
    op.create_index("ix_trip_end_point_id", "trip", ["end_point_id"], unique=False)
    op.create_index("ix_trip_vehicle_id", "trip", ["vehicle_id"], unique=False)

    op.create_foreign_key(
        "fk_trip_start_point_id_vehicle_gps_point",
        "trip",
        "vehicle_gps_point",
        ["start_point_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_trip_end_point_id_vehicle_gps_point",
        "trip",
        "vehicle_gps_point",
        ["end_point_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_constraint(
        "fk_trip_start_point_id_vehicle_gps_point",
        "trip",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_trip_end_point_id_vehicle_gps_point",
        "trip",
        type_="foreignkey",
    )

    op.drop_index("ix_trip_vehicle_id", table_name="trip")
    op.drop_index("ix_trip_start_point_id", table_name="trip")
    op.drop_index("ix_trip_end_point_id", table_name="trip")

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

    op.drop_column("trip", "end_point_id")
    op.drop_column("trip", "start_point_id")
