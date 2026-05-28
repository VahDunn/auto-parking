from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_for_user(
        self,
        *,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.recipient_user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )

        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))

        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def create_many(self, payloads: list[dict[str, Any]]) -> Sequence[Notification]:
        if not payloads:
            return []

        notifications = [Notification(**payload) for payload in payloads]
        self.db.add_all(notifications)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        ids = [notification.id for notification in notifications]
        result = await self.db.execute(
            select(Notification)
            .where(Notification.id.in_(ids))
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )
        return result.unique().scalars().all()

    async def mark_read(self, *, user_id: int, notification_id: int) -> Notification | None:
        notification = await self._get_for_user(user_id=user_id, notification_id=notification_id)
        if notification is None:
            return None

        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
            await self.db.refresh(notification)

        return notification

    async def mark_all_read(self, *, user_id: int) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return result.rowcount or 0

    async def unread_count(self, *, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def _get_for_user(
        self,
        *,
        user_id: int,
        notification_id: int,
    ) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
