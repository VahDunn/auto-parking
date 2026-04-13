from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models import Vehicle


class VehicleGpsPoint(BaseORM):
    __tablename__ = "vehicle_gps_point"

    vehicle_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
        nullable=False,
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="points",
        lazy="selectin",
    )

    recorded_at_utc: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    position: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    __table_args__ = (
        sa.Index(
            "ix_vehicle_gps_point_vehicle_id_recorded_at_utc",
            "vehicle_id",
            "recorded_at_utc",
        ),
        sa.Index(
            "ix_vehicle_gps_point_position_gist",
            "position",
            postgresql_using="gist",
        ),
    )
