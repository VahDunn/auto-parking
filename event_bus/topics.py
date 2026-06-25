from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KafkaTopicSpec:
    name: str
    partitions: int
    replication_factor: int
    key_description: str
    description: str


VEHICLE_EVENTS_TOPIC = "auto-parking.vehicle.events"
AUDIT_EVENTS_TOPIC = "auto-parking.audit.events"
GPS_EVENTS_TOPIC = "auto-parking.gps.events"

KAFKA_TOPICS: tuple[KafkaTopicSpec, ...] = (
    KafkaTopicSpec(
        name=VEHICLE_EVENTS_TOPIC,
        partitions=3,
        replication_factor=1,
        key_description="vehicle_id",
        description="CRUD-события машин для подписчиков бизнес-событий",
    ),
    KafkaTopicSpec(
        name=AUDIT_EVENTS_TOPIC,
        partitions=3,
        replication_factor=1,
        key_description="entity_id, иначе event_id",
        description="Единый поток audit-событий от сервисов проекта",
    ),
    KafkaTopicSpec(
        name=GPS_EVENTS_TOPIC,
        partitions=6,
        replication_factor=1,
        key_description="vehicle_id",
        description="Live GPS-точки генератора треков",
    ),
)
