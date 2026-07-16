from functools import lru_cache

from auto_parking.core.config import settings
from auto_parking.infrastructure.events import KafkaEventConsumer, KafkaEventProducer
from event_bus.contracts import EventConsumer, EventProducer


@lru_cache
def get_event_producer() -> EventProducer:
    return KafkaEventProducer(_kafka_bootstrap_servers())


def get_event_consumer(
    group_id: str,
    *,
    auto_offset_reset: str = "earliest",
) -> EventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=_kafka_bootstrap_servers(),
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
    )


async def close_event_producer() -> None:
    if get_event_producer.cache_info().currsize == 0:
        return
    await get_event_producer().close()


def _kafka_bootstrap_servers() -> str:
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required for Kafka event bus")
    return settings.kafka_bootstrap_servers
