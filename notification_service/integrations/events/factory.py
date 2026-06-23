from redis.asyncio import Redis

from notification_service.core.config import Settings
from notification_service.integrations.events.kafka import KafkaEventConsumer
from notification_service.integrations.events.null import NullEventConsumer
from notification_service.integrations.events.redis import RedisEventConsumer
from notification_service.ports.events import EventConsumer


def create_event_consumer(settings: Settings) -> EventConsumer:
    backend = settings.event_bus_backend.lower()
    if backend == "kafka":
        return KafkaEventConsumer(
            bootstrap_servers=_kafka_bootstrap_servers(settings),
            group_id=settings.kafka_notification_consumer_group,
        )
    if backend == "redis" and settings.redis_url:
        redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        return RedisEventConsumer(redis)
    return NullEventConsumer()


def _kafka_bootstrap_servers(settings: Settings) -> str:
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required for Kafka event bus")
    return settings.kafka_bootstrap_servers
