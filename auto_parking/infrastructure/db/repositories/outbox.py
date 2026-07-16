from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.infrastructure.db.models import OutboxEvent
from event_bus.contracts import EventEnvelope


class OutboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_event(
        self,
        *,
        topic: str,
        event: EventEnvelope,
        key: str | None = None,
    ) -> OutboxEvent:
        outbox_event = OutboxEvent(
            topic=topic,
            key=key,
            event_id=event.event_id,
            event_type=event.event_type,
            entity=event.entity,
            entity_id=str(event.entity_id) if event.entity_id is not None else None,
            payload=event.to_dict(),
            status="pending",
            attempts=0,
        )
        self.db.add(outbox_event)
        await self.db.flush()
        return outbox_event

    async def get_pending_for_update(
        self,
        *,
        limit: int,
        now: datetime | None = None,
    ) -> Sequence[OutboxEvent]:
        now = now or datetime.now(UTC)
        result = await self.db.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == "pending",
                or_(
                    OutboxEvent.next_attempt_at.is_(None),
                    OutboxEvent.next_attempt_at <= now,
                ),
            )
            .order_by(OutboxEvent.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = result.scalars().all()
        for event in events:
            event.locked_at = now
        return events

    async def mark_published(
        self,
        event: OutboxEvent,
        *,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        event.status = "published"
        event.published_at = now
        event.locked_at = None
        event.last_error = None

    async def mark_failed(
        self,
        event: OutboxEvent,
        error: Exception,
        *,
        max_attempts: int,
        retry_delay_seconds: int,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        event.attempts += 1
        event.locked_at = None
        event.last_error = str(error)[:2000]

        if event.attempts >= max_attempts:
            event.status = "failed"
            event.next_attempt_at = None
            return

        event.status = "pending"
        event.next_attempt_at = now + timedelta(seconds=retry_delay_seconds)
