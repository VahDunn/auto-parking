from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models import Enterprise, Vehicle


class Driver(BaseORM):
    __tablename__ = "driver"
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    salary_rub: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    enterprise_id: Mapped[int] = mapped_column(
        sa.ForeignKey(
            "enterprise.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    enterprise: Mapped["Enterprise"] = relationship(
        back_populates="drivers",
        lazy="selectin",
    )
    active_vehicle: Mapped["Vehicle | None"] = relationship(
        "Vehicle",
        back_populates="active_driver",
        uselist=False,
        foreign_keys="Vehicle.active_driver_id",
        lazy="selectin",
    )

    vehicles: Mapped[list["Vehicle"]] = relationship(
        "Vehicle",
        secondary="vehicle_driver_assignment",
        lazy="selectin",
        back_populates="drivers",
    )

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"{self.name}"
