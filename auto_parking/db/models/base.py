from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import functions as sa_func


class Base(AsyncAttrs, DeclarativeBase):
    """Base ORM Model class."""


class BaseORM(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        sa.FetchedValue(),
        server_default=sa_func.now(),
        nullable=False,
    )
