import pytest

from notification_service.ports.events import AUDIT_EVENTS_TOPIC, EventEnvelope
from notification_service.service import VehicleEventNotificationService

pytestmark = pytest.mark.asyncio


class FakeBotSessionRegistry:
    def __init__(self, chat_ids: dict[int, int]) -> None:
        self._chat_ids = chat_ids
        self.requested_user_ids: list[int] = []

    async def get_telegram_chat_id(self, *, user_id: int) -> int | None:
        self.requested_user_ids.append(user_id)
        return self._chat_ids.get(user_id)


class FakeTelegramSender:
    def __init__(self, result: bool = True) -> None:
        self.messages: list[tuple[int, str]] = []
        self._result = result

    async def send_message(self, *, chat_id: int, text: str) -> bool:
        self.messages.append((chat_id, text))
        return self._result


class FakeEventProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, EventEnvelope, str | None]] = []

    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
        *,
        key: str | None = None,
    ) -> None:
        self.messages.append((topic, event, key))

    async def close(self) -> None:
        return None


def vehicle_event(
    *,
    event_type: str = "vehicle.updated",
    payload: dict | None = None,
) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=event_type,
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=7,
        payload=payload
        or {
            "vehicle_id": 7,
            "vehicle_number": "А123ВС77",
            "enterprise_id": 2,
            "manager_user_ids": [11, 12],
        },
    )


async def test_vehicle_event_notification_sends_to_logged_in_managers_from_event_payload():
    registry = FakeBotSessionRegistry({11: 420011})
    sender = FakeTelegramSender()
    service = VehicleEventNotificationService(
        telegram_session_registry=registry,
        telegram_sender=sender,
    )

    await service.handle(vehicle_event())

    assert registry.requested_user_ids == [11, 12]
    assert sender.messages == [(420011, "Автомобиль А123ВС77: обновлен.")]


async def test_vehicle_event_notification_skips_non_vehicle_events():
    sender = FakeTelegramSender()
    service = VehicleEventNotificationService(
        telegram_session_registry=FakeBotSessionRegistry({11: 420011}),
        telegram_sender=sender,
    )
    event = EventEnvelope.create(
        event_type="driver.updated",
        producer="auto-parking-api",
        entity="driver",
        entity_id=3,
        payload={"manager_user_ids": [11]},
    )

    await service.handle(event)

    assert sender.messages == []


async def test_vehicle_event_notification_skips_events_without_managers():
    registry = FakeBotSessionRegistry({11: 420011})
    sender = FakeTelegramSender()
    service = VehicleEventNotificationService(
        telegram_session_registry=registry,
        telegram_sender=sender,
    )

    await service.handle(
        vehicle_event(payload={"vehicle_id": 7, "vehicle_number": "А123ВС77"})
    )

    assert registry.requested_user_ids == []
    assert sender.messages == []


async def test_vehicle_event_notification_uses_entity_id_when_number_missing():
    sender = FakeTelegramSender()
    service = VehicleEventNotificationService(
        telegram_session_registry=FakeBotSessionRegistry({11: 420011}),
        telegram_sender=sender,
    )

    await service.handle(
        vehicle_event(
            event_type="vehicle.deleted",
            payload={"vehicle_id": 7, "enterprise_id": 2, "manager_user_ids": [11]},
        )
    )

    assert sender.messages == [(420011, "Автомобиль #7: удален.")]


async def test_vehicle_event_notification_publishes_audit_event_after_send():
    sender = FakeTelegramSender()
    producer = FakeEventProducer()
    service = VehicleEventNotificationService(
        telegram_session_registry=FakeBotSessionRegistry({11: 420011}),
        telegram_sender=sender,
        audit_event_producer=producer,
    )

    await service.handle(
        vehicle_event(
            payload={
                "vehicle_id": 7,
                "vehicle_number": "А123ВС77",
                "enterprise_id": 2,
                "manager_user_ids": [11],
            },
        )
    )

    assert len(producer.messages) == 1
    topic, event, key = producer.messages[0]
    assert topic == AUDIT_EVENTS_TOPIC
    assert key == "11"
    assert event.event_type == "notification.telegram.sent"
    assert event.producer == "notification-service"
    assert event.entity == "telegram_notification"
    assert event.entity_id == 11
    assert event.payload["manager_user_id"] == 11
    assert event.payload["telegram_chat_id"] == 420011
    assert event.payload["vehicle_id"] == 7
    assert event.payload["source_event_type"] == "vehicle.updated"
    assert event.payload["result"] == "sent"


async def test_vehicle_event_notification_publishes_failed_audit_event():
    sender = FakeTelegramSender(result=False)
    producer = FakeEventProducer()
    service = VehicleEventNotificationService(
        telegram_session_registry=FakeBotSessionRegistry({11: 420011}),
        telegram_sender=sender,
        audit_event_producer=producer,
    )

    await service.handle(vehicle_event(payload={"vehicle_id": 7, "manager_user_ids": [11]}))

    _, event, _ = producer.messages[0]
    assert event.event_type == "notification.telegram.failed"
    assert event.payload["result"] == "failed"
