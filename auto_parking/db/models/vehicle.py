import sqlalchemy as sa
from sqlalchemy.orm import Mapped, relationship

from auto_parking.db.models.base import BaseORM, mapped_column
from auto_parking.db.models.vehicle_model import VehicleModel


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
