from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.infrastructure.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.infrastructure.db.models.enterprise import Enterprise


class User(BaseORM):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(sa.String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="user_role"),
        nullable=False,
        index=True,
        default=UserRole.user,
        server_default=UserRole.user.value,
    )

    enterprises: Mapped[list[Enterprise]] = relationship(
        secondary="user_enterprise",
        back_populates="users",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, role={self.role!r})"
