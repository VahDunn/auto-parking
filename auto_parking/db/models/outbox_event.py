from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from auto_parking.db.models.base import BaseORM


class OutboxEvent(BaseORM):
    __tablename__ = "outbox_event"

    topic: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    event_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        server_default="pending",
        index=True,
    )
    attempts: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default="0",
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "topic",
            "event_id",
            name="uq_outbox_event_topic_event_id",
        ),
        sa.Index(
            "ix_outbox_event_pending_next_attempt_id",
            "next_attempt_at",
            "id",
            postgresql_where=sa.text("status = 'pending'"),
        ),
    )
