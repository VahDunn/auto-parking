from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM
from auto_parking.db.models.vehicle_model import VehicleModel

if TYPE_CHECKING:
    from auto_parking.db.models import Driver, Enterprise


class Vehicle(BaseORM):
    __tablename__ = "vehicle"
    price: Mapped[int] = mapped_column(sa.BigInteger)
    mileage: Mapped[int] = mapped_column(sa.BigInteger)
    vehicle_number: Mapped[int] = mapped_column(sa.String, unique=True)
    owners_count: Mapped[int] = mapped_column(sa.Integer)
    accident_number: Mapped[int] = mapped_column(sa.Integer)
    manufacture_year = mapped_column(sa.SmallInteger)
    model_id: Mapped[int] = mapped_column(
        sa.ForeignKey("vehicle_model.id"),
        nullable=False,
        index=True,
    )
    model: Mapped[VehicleModel] = relationship(
        "VehicleModel",
        lazy="selectin",
    )
    enterprise_id: Mapped[int] = mapped_column(
        sa.ForeignKey("enterprise.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enterprise: Mapped["Enterprise"] = relationship(
        back_populates="vehicles",
        lazy="selectin",
    )
    active_driver_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("driver.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
        index=True,
    )
    active_driver: Mapped["Driver | None"] = relationship(
        "Driver",
        foreign_keys=[active_driver_id],
        back_populates="active_vehicle",
        lazy="selectin",
    )
