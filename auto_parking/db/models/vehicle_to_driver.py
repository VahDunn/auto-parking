import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from auto_parking.db.models import Base


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
