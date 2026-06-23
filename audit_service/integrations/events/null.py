import logging
from collections.abc import Sequence

from audit_service.ports.events import EventEnvelope, EventHandler

logger = logging.getLogger(__name__)


class NullEventProducer:
    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
        *,
        key: str | None = None,
    ) -> None:
        logger.debug("Event ignored: topic=%s event_type=%s key=%s", topic, event.event_type, key)

    async def close(self) -> None:
        return None


class NullEventConsumer:
    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        return None

    async def stop(self) -> None:
        return None
