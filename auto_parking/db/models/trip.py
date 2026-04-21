from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models import Vehicle, VehicleGpsPoint


class Trip(BaseORM):
    __tablename__: str = "trip"

    vehicle_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at_utc: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    ended_at_utc: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    start_point_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle_gps_point.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    end_point_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle_gps_point.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        lazy="selectin",
    )

    start_point: Mapped["VehicleGpsPoint"] = relationship(
        "VehicleGpsPoint",
        foreign_keys=[start_point_id],
        lazy="selectin",
    )

    end_point: Mapped["VehicleGpsPoint"] = relationship(
        "VehicleGpsPoint",
        foreign_keys=[end_point_id],
        lazy="selectin",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "ended_at_utc >= started_at_utc",
            name="ck_trip_ended_at_gte_started_at",
        ),
        sa.Index(
            "ix_trip_vehicle_id_started_at_utc_ended_at_utc",
            "vehicle_id",
            "started_at_utc",
            "ended_at_utc",
        ),
    )
