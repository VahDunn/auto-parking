from __future__ import annotations

import asyncio
import logging

from notification_service.core.config import get_settings
from notification_service.integrations.events import create_event_consumer, create_event_producer
from notification_service.integrations.redis_sessions import RedisTelegramSessionRegistry
from notification_service.integrations.telegram import TelegramBotSender
from notification_service.ports.events import VEHICLE_EVENTS_TOPIC
from notification_service.service import VehicleEventNotificationService

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run notification-service")

    telegram_session_registry = RedisTelegramSessionRegistry(settings.redis_url)
    telegram_sender = TelegramBotSender(settings.telegram_bot_token)
    audit_event_producer = create_event_producer(settings)
    service = VehicleEventNotificationService(
        telegram_session_registry=telegram_session_registry,
        telegram_sender=telegram_sender,
        audit_event_producer=audit_event_producer,
    )
    consumer = create_event_consumer(settings)

    try:
        logger.info("Notification microservice started: topic=%s", VEHICLE_EVENTS_TOPIC)
        await consumer.subscribe([VEHICLE_EVENTS_TOPIC], service.handle)
    finally:
        await consumer.stop()
        await audit_event_producer.close()
        await telegram_session_registry.close()


if __name__ == "__main__":
    asyncio.run(main())
