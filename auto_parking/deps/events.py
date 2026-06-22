from functools import lru_cache

from redis.asyncio import Redis

from auto_parking.core.config import settings
from auto_parking.integrations.events import (
    KafkaEventConsumer,
    KafkaEventProducer,
    NullEventConsumer,
    NullEventProducer,
    RedisEventConsumer,
    RedisEventProducer,
)
from auto_parking.ports.events import EventConsumer, EventProducer


@lru_cache
def get_event_producer() -> EventProducer:
    backend = settings.event_bus_backend.lower()
    if backend == "kafka":
        return KafkaEventProducer(settings.kafka_bootstrap_servers)
    if backend == "redis" and settings.redis_url:
        return RedisEventProducer(_redis_client())
    return NullEventProducer()


def get_event_consumer(group_id: str | None = None) -> EventConsumer:
    backend = settings.event_bus_backend.lower()
    if backend == "kafka":
        return KafkaEventConsumer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=group_id or settings.kafka_notification_consumer_group,
        )
    if backend == "redis" and settings.redis_url:
        return RedisEventConsumer(_redis_client())
    return NullEventConsumer()


async def close_event_producer() -> None:
    await get_event_producer().close()


def _redis_client() -> Redis:
    if settings.redis_url is None:
        raise RuntimeError("REDIS_URL is required for Redis event bus")
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
