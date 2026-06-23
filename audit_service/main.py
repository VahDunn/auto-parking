from __future__ import annotations

import asyncio
import logging

from audit_service.core.config import get_settings
from audit_service.integrations.events import create_event_consumer, create_event_producer
from audit_service.ports.events import VEHICLE_EVENTS_TOPIC
from audit_service.service import AuditEventService

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    producer = create_event_producer(settings)
    service = AuditEventService(producer)
    consumer = create_event_consumer(settings)

    try:
        logger.info("Audit microservice started: topic=%s", VEHICLE_EVENTS_TOPIC)
        await consumer.subscribe([VEHICLE_EVENTS_TOPIC], service.handle)
    finally:
        await consumer.stop()
        await producer.close()


if __name__ == "__main__":
    asyncio.run(main())
