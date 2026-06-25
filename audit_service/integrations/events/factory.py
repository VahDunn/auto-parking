from audit_service.core.config import Settings
from audit_service.integrations.events.kafka import KafkaEventConsumer
from audit_service.ports.events import EventConsumer


def create_event_consumer(settings: Settings) -> EventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=_kafka_bootstrap_servers(settings),
        group_id=settings.kafka_audit_source_consumer_group,
    )


def _kafka_bootstrap_servers(settings: Settings) -> str:
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required for Kafka event bus")
    return settings.kafka_bootstrap_servers
