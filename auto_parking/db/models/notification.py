from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.core.domain.enums.notification_type import NotificationType
from auto_parking.db.models.base import BaseORM


class Notification(BaseORM):
    __tablename__ = "notification"

    recipient_user_id: Mapped[int] = mapped_column(
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enterprise_id: Mapped[int] = mapped_column(
        sa.ForeignKey("enterprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trip_id: Mapped[int] = mapped_column(
        sa.ForeignKey("trip.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        sa.String(64),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    recipient = relationship("User", lazy="selectin")
    enterprise = relationship("Enterprise", lazy="selectin")
    trip = relationship("Trip", lazy="selectin")

    __table_args__ = (
        sa.UniqueConstraint(
            "recipient_user_id",
            "type",
            "trip_id",
            name="uq_notification_recipient_type_trip",
        ),
        sa.Index(
            "ix_notification_recipient_read_created",
            "recipient_user_id",
            "read_at",
            "created_at",
        ),
        sa.Index(
            "ix_notification_recipient_created_id",
            "recipient_user_id",
            "created_at",
            "id",
        ),
        sa.Index(
            "ix_notification_unread_recipient_created_id",
            "recipient_user_id",
            "created_at",
            "id",
            postgresql_where=sa.text("read_at IS NULL"),
        ),
    )
