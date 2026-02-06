from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models import Base

if TYPE_CHECKING:
    from auto_parking.db.models import Driver, Vehicle


class VehicleDriverAssignment(Base):
    __tablename__ = "vehicle_driver_assignment"

    vehicle_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
        primary_key=True,
    )
    driver_id: Mapped[int] = mapped_column(
        sa.ForeignKey("driver.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle", lazy="selectin", overlaps="drivers,vehicles"
    )
    driver: Mapped["Driver"] = relationship("Driver", lazy="selectin", overlaps="drivers,vehicles")

    def __str__(self) -> str:
        return f"{self.vehicle} — {self.driver}"
