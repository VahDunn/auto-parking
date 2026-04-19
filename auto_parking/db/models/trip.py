from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models import Vehicle


class Trip(BaseORM):
    __tablename__ = "trip"

    vehicle_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
        nullable=False,
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="trips",
        lazy="selectin",
    )

    started_at_utc: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    ended_at_utc: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        sa.Index(
            "ix_trip_vehicle_id_started_at_utc",
            "vehicle_id",
            "started_at_utc",
        ),
        sa.Index(
            "ix_trip_vehicle_id_ended_at_utc",
            "vehicle_id",
            "ended_at_utc",
        ),
        sa.Index(
            "ix_trip_vehicle_id_started_at_utc_ended_at_utc",
            "vehicle_id",
            "started_at_utc",
            "ended_at_utc",
        ),
        sa.CheckConstraint(
            "ended_at_utc >= started_at_utc",
            name="ck_trip_ended_at_gte_started_at",
        ),
    )
