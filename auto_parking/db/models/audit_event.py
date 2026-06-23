from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from auto_parking.db.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    producer: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    entity: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    consumed_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    __table_args__ = (
        sa.Index("ix_audit_event_entity", "entity", "entity_id"),
        sa.Index("ix_audit_event_event_type", "event_type"),
        sa.Index("ix_audit_event_occurred_at", "occurred_at"),
    )
