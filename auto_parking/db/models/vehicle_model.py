import sqlalchemy as sa

from auto_parking.db.models.base import BaseORM, mapped_column


class VehicleModel(BaseORM):
    __tablename__ = "vehicle_model"
    name = mapped_column(sa.String)
    type = mapped_column(sa.String)
    horse_powers = mapped_column(sa.Integer)
    seats_number = mapped_column(sa.Integer)
    fuel_capacity_liters = mapped_column(sa.Integer)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"{self.name}, {self.type}"
