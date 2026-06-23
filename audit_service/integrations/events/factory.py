from redis.asyncio import Redis

from audit_service.core.config import Settings
from audit_service.integrations.events.kafka import KafkaEventConsumer, KafkaEventProducer
from audit_service.integrations.events.null import NullEventConsumer, NullEventProducer
from audit_service.integrations.events.redis import RedisEventConsumer, RedisEventProducer
from audit_service.ports.events import EventConsumer, EventProducer


def create_event_producer(settings: Settings) -> EventProducer:
    backend = settings.event_bus_backend.lower()
    if backend == "kafka":
        return KafkaEventProducer(_kafka_bootstrap_servers(settings))
    if backend == "redis" and settings.redis_url:
        redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        return RedisEventProducer(redis)
    return NullEventProducer()


def create_event_consumer(settings: Settings) -> EventConsumer:
    backend = settings.event_bus_backend.lower()
    if backend == "kafka":
        return KafkaEventConsumer(
            bootstrap_servers=_kafka_bootstrap_servers(settings),
            group_id=settings.kafka_audit_source_consumer_group,
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
