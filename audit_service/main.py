from __future__ import annotations

import asyncio
import logging

from audit_service.core.config import get_settings
from audit_service.db import AsyncSessionLocal, close_db, init_db
from audit_service.integrations.events import create_event_consumer
from audit_service.repo import AuditEventRepository
from audit_service.service import AuditEventService
from event_bus.contracts import AUDIT_EVENTS_TOPIC, EventEnvelope

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    await init_db()
    consumer = create_event_consumer(settings)

    try:
        logger.info("Audit microservice started: topic=%s", AUDIT_EVENTS_TOPIC)
        await consumer.subscribe([AUDIT_EVENTS_TOPIC], _handle_event)
    finally:
        await consumer.stop()
        await close_db()


async def _handle_event(event: EventEnvelope) -> None:
    async with AsyncSessionLocal() as session:
        await AuditEventService(AuditEventRepository(session)).handle(event)


if __name__ == "__main__":
    asyncio.run(main())
