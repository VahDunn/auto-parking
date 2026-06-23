import asyncio
import logging
from collections.abc import Sequence

from notification_service.ports.events import EventHandler

logger = logging.getLogger(__name__)


class NullEventConsumer:
    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        logger.warning("Event consumer disabled, topics ignored: %s", ", ".join(topics))
        while True:
            await asyncio.sleep(3600)

    async def stop(self) -> None:
        return None
