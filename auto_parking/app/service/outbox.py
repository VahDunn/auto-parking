import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.app.ports.events import EventEnvelope, EventProducer
from auto_parking.infrastructure.db.repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(
        self,
        *,
        sessionmaker: async_sessionmaker[AsyncSession],
        producer_factory: Callable[[], EventProducer],
        batch_size: int = 100,
        poll_interval_seconds: float = 1.0,
        retry_delay_seconds: int = 5,
        max_attempts: int = 10,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._producer_factory = producer_factory
        self._batch_size = batch_size
        self._poll_interval_seconds = poll_interval_seconds
        self._retry_delay_seconds = retry_delay_seconds
        self._max_attempts = max_attempts
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="outbox-dispatcher")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is None:
            return
        await self._task
        self._task = None

    async def dispatch_once(self) -> int:
        producer = self._producer_factory()
        async with self._sessionmaker() as session:
            async with session.begin():
                repo = OutboxRepository(session)
                events = await repo.get_pending_for_update(limit=self._batch_size)
                for outbox_event in events:
                    try:
                        event = EventEnvelope.from_dict(outbox_event.payload)
                        await producer.publish(
                            outbox_event.topic,
                            event,
                            key=outbox_event.key,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Outbox publish failed: id=%s topic=%s event_type=%s",
                            outbox_event.id,
                            outbox_event.topic,
                            outbox_event.event_type,
                            exc_info=True,
                        )
                        await repo.mark_failed(
                            outbox_event,
                            exc,
                            max_attempts=self._max_attempts,
                            retry_delay_seconds=self._retry_delay_seconds,
                        )
                    else:
                        await repo.mark_published(outbox_event)
                return len(events)

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                await self.dispatch_once()
            except Exception:
                logger.warning("Outbox dispatcher iteration failed", exc_info=True)

            try:
                await asyncio.wait_for(
                    self._stopped.wait(),
                    timeout=self._poll_interval_seconds,
                )
            except TimeoutError:
                pass
