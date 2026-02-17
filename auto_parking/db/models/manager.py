from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models.enterprise import Enterprise


class Manager(BaseORM):
    __tablename__ = "manager"

    username: Mapped[str] = mapped_column(sa.String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    enterprises: Mapped[list["Enterprise"]] = relationship(
        secondary="manager_enterprise",
        back_populates="managers",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Manager(username={self.username!r})"
