import asyncio
import logging
from collections.abc import Sequence

from auto_parking.ports.events import EventEnvelope, EventHandler

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
        logger.warning("Event consumer disabled, topics ignored: %s", ", ".join(topics))
        while True:
            await asyncio.sleep(3600)

    async def stop(self) -> None:
        return None
