from types import SimpleNamespace

import pytest

from audit_service.integrations.events import factory as audit_factory
from auto_parking.app.deps import events as api_events
from event_bus.kafka import KafkaEventConsumer, KafkaEventProducer
from event_bus.topics import (
    AUDIT_EVENTS_TOPIC,
    GPS_EVENTS_TOPIC,
    KAFKA_TOPICS,
    VEHICLE_EVENTS_TOPIC,
)
from notification_service.integrations.events import factory as notification_factory


def settings(**overrides):
    data = {
        "kafka_bootstrap_servers": "kafka:9092",
        "kafka_notification_consumer_group": "notifications",
        "kafka_audit_source_consumer_group": "audit-source",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_api_event_bus_requires_kafka_bootstrap_servers(monkeypatch):
    api_events.get_event_producer.cache_clear()
    monkeypatch.setattr(api_events, "settings", settings(kafka_bootstrap_servers=None))

    with pytest.raises(RuntimeError, match="KAFKA_BOOTSTRAP_SERVERS"):
        api_events.get_event_producer()

    api_events.get_event_producer.cache_clear()


def test_api_event_bus_uses_kafka_bootstrap(monkeypatch):
    api_events.get_event_producer.cache_clear()
    monkeypatch.setattr(api_events, "settings", settings())

    producer = api_events.get_event_producer()

    assert isinstance(producer, KafkaEventProducer)
    assert producer._bootstrap_servers == "kafka:9092"
    api_events.get_event_producer.cache_clear()


def test_notification_event_bus_uses_kafka_consumer():
    producer = notification_factory.create_event_producer(settings())
    consumer = notification_factory.create_event_consumer(settings())

    assert isinstance(producer, KafkaEventProducer)
    assert isinstance(consumer, KafkaEventConsumer)
    assert producer._bootstrap_servers == "kafka:9092"
    assert consumer._bootstrap_servers == "kafka:9092"
    assert consumer._group_id == "notifications"


def test_audit_event_bus_uses_kafka_consumer():
    consumer = audit_factory.create_event_consumer(settings())

    assert isinstance(consumer, KafkaEventConsumer)
    assert consumer._bootstrap_servers == "kafka:9092"
    assert consumer._group_id == "audit-source"


def test_kafka_topics_are_defined_in_one_contract():
    topic_names = {topic.name for topic in KAFKA_TOPICS}

    assert topic_names == {VEHICLE_EVENTS_TOPIC, AUDIT_EVENTS_TOPIC, GPS_EVENTS_TOPIC}
    assert all(topic.partitions > 1 for topic in KAFKA_TOPICS)
    assert all(topic.replication_factor == 1 for topic in KAFKA_TOPICS)
