from __future__ import annotations

import asyncio
import logging

from notification_service.core.config import get_settings
from notification_service.integrations.events import create_event_consumer
from notification_service.integrations.postgres import (
    PostgresManagerLookup,
    create_engine_and_session_factory,
)
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

    engine, session_factory = create_engine_and_session_factory(
        settings.database_url,
        debug=settings.debug,
    )
    manager_lookup = PostgresManagerLookup(session_factory)
    telegram_session_registry = RedisTelegramSessionRegistry(settings.redis_url)
    telegram_sender = TelegramBotSender(settings.telegram_bot_token)
    service = VehicleEventNotificationService(
        manager_lookup=manager_lookup,
        telegram_session_registry=telegram_session_registry,
        telegram_sender=telegram_sender,
    )
    consumer = create_event_consumer(settings)

    try:
        logger.info("Notification microservice started: topic=%s", VEHICLE_EVENTS_TOPIC)
        await consumer.subscribe([VEHICLE_EVENTS_TOPIC], service.handle)
    finally:
        await consumer.stop()
        await telegram_session_registry.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
