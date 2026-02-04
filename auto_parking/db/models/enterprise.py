from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models.driver import Driver
    from auto_parking.db.models.vehicle import Vehicle


class Enterprise(BaseORM):
    __tablename__ = "enterprise"
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    settlement: Mapped[str] = mapped_column(sa.String, nullable=False)
    drivers: Mapped[list["Driver"]] = relationship(
        back_populates="enterprise", cascade="save-update, merge", lazy="selectin"
    )
    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="enterprise", cascade="save-update, merge", lazy="selectin"
    )

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"{self.name}"
