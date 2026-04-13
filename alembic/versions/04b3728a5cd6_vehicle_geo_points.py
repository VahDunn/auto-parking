"""vehicle_geo_points

Revision ID: 04b3728a5cd6
Revises: c1a29ed3b93f
Create Date: 2026-04-12 07:01:51.762344
"""

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

# revision identifiers, used by Alembic.
revision = "04b3728a5cd6"
down_revision = "c1a29ed3b93f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "vehicle_gps_point",
        sa.Column(
            "vehicle_id",
            sa.BigInteger(),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "position",
            Geometry(geometry_type="POINT", srid=4326),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_vehicle_gps_point_vehicle_id_recorded_at_utc",
        "vehicle_gps_point",
        ["vehicle_id", "recorded_at_utc"],
        unique=False,
    )

    op.create_index(
        "ix_vehicle_gps_point_position_gist",
        "vehicle_gps_point",
        ["position"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade():
    op.drop_index(
        "ix_vehicle_gps_point_position_gist",
        table_name="vehicle_gps_point",
    )
    op.drop_index(
        "ix_vehicle_gps_point_vehicle_id_recorded_at_utc",
        table_name="vehicle_gps_point",
    )
    op.drop_table("vehicle_gps_point")
