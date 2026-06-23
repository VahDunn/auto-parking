import asyncio
import logging

from auto_parking.core.config import settings
from auto_parking.db.engine import AsyncSessionLocal
from auto_parking.deps.events import get_event_consumer
from auto_parking.ports.events import AUDIT_EVENTS_TOPIC, EventConsumer, EventEnvelope
from auto_parking.repo.audit import AuditEventRepository
from auto_parking.service.audit import AuditEventService

logger = logging.getLogger(__name__)


class AuditEventConsumerRunner:
    def __init__(self) -> None:
        self._consumer: EventConsumer | None = None
        self._task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        if not settings.audit_consumer_enabled:
            logger.info("Audit event consumer disabled")
            return
        if self._task is not None:
            return

        self._stopping = False
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopping = True
        if self._consumer is not None:
            await self._consumer.stop()

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._consumer = None

    async def _run(self) -> None:
        while not self._stopping:
            self._consumer = get_event_consumer(settings.kafka_audit_consumer_group)
            try:
                await self._consumer.subscribe([AUDIT_EVENTS_TOPIC], self._handle)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Audit event consumer stopped unexpectedly, retrying")
                if not self._stopping:
                    await asyncio.sleep(1)
            finally:
                if self._consumer is not None:
                    await self._consumer.stop()
                    self._consumer = None

    @staticmethod
    async def _handle(event: EventEnvelope) -> None:
        async with AsyncSessionLocal() as session:
            await AuditEventService(AuditEventRepository(session)).store(event)


audit_event_consumer = AuditEventConsumerRunner()
