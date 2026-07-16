from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.infrastructure.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.infrastructure.db.models import Driver, User, Vehicle


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

    users: Mapped[list["User"]] = relationship(
        secondary="user_enterprise",
        back_populates="enterprises",
        lazy="selectin",
    )
    timezone: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"{self.name}"


user_enterprise = sa.Table(
    "user_enterprise",
    BaseORM.metadata,
    sa.Column("user_id", sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    sa.Column(
        "enterprise_id", sa.ForeignKey("enterprise.id", ondelete="CASCADE"), primary_key=True
    ),
    sa.UniqueConstraint("user_id", "enterprise_id", name="uq_user_enterprise"),
    sa.Index("ix_user_enterprise_enterprise_user", "enterprise_id", "user_id"),
)
