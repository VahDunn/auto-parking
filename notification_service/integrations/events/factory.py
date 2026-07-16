from event_bus.contracts import EventConsumer, EventProducer
from notification_service.core.config import Settings
from notification_service.integrations.events.kafka import KafkaEventConsumer, KafkaEventProducer


def create_event_producer(settings: Settings) -> EventProducer:
    return KafkaEventProducer(_kafka_bootstrap_servers(settings))


def create_event_consumer(settings: Settings) -> EventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=_kafka_bootstrap_servers(settings),
        group_id=settings.kafka_notification_consumer_group,
    )


def _kafka_bootstrap_servers(settings: Settings) -> str:
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required for Kafka event bus")
    return settings.kafka_bootstrap_servers
