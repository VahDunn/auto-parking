from collections import defaultdict

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from audit_service.db.models import AuditEvent
from audit_service.db.models import Base as AuditBase
from audit_service.repo import AuditEventRepository
from audit_service.service import AuditEventService
from event_bus.contracts import (
    AUDIT_EVENTS_TOPIC,
    VEHICLE_EVENTS_TOPIC,
    EventEnvelope,
    EventHandler,
)
from notification_service.service import VehicleEventNotificationService

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


class InMemoryEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self.published: list[tuple[str, EventEnvelope, str | None]] = []

    async def subscribe(self, topics, handler: EventHandler) -> None:
        for topic in topics:
            self._handlers[topic].append(handler)

    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
        *,
        key: str | None = None,
    ) -> None:
        self.published.append((topic, event, key))
        for handler in self._handlers[topic]:
            await handler(event)

    async def close(self) -> None:
        return None

    async def stop(self) -> None:
        return None


class FakeTelegramSessionRegistry:
    def __init__(self, sessions: dict[int, int]) -> None:
        self._sessions = sessions

    async def get_telegram_chat_id(self, *, user_id: int) -> int | None:
        return self._sessions.get(user_id)


class FakeTelegramSender:
    def __init__(self, *, result: bool = True) -> None:
        self._result = result
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, *, chat_id: int, text: str) -> bool:
        self.messages.append((chat_id, text))
        return self._result


async def prepare_audit_tables(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker() as session:
        conn = await session.connection()
        await conn.run_sync(AuditBase.metadata.drop_all)
        await conn.run_sync(AuditBase.metadata.create_all)
        await session.commit()


async def fetch_audit_events(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> list[AuditEvent]:
    async with sessionmaker() as session:
        result = await session.execute(select(AuditEvent).order_by(AuditEvent.id))
        return list(result.scalars().all())


async def test_vehicle_event_flows_from_api_topic_to_notification_and_audit_service(
    integration_sessionmaker,
):
    await prepare_audit_tables(integration_sessionmaker)
    bus = InMemoryEventBus()
    telegram_sender = FakeTelegramSender()
    notification_service = VehicleEventNotificationService(
        telegram_session_registry=FakeTelegramSessionRegistry({10: 9001}),
        telegram_sender=telegram_sender,
        audit_event_producer=bus,
    )

    async def store_audit_event(event: EventEnvelope) -> None:
        async with integration_sessionmaker() as session:
            await AuditEventService(AuditEventRepository(session)).handle(event)

    await bus.subscribe([VEHICLE_EVENTS_TOPIC], notification_service.handle)
    await bus.subscribe([AUDIT_EVENTS_TOPIC], store_audit_event)

    source_event = EventEnvelope.create(
        event_type="vehicle.updated",
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=42,
        payload={
            "vehicle_id": 42,
            "vehicle_number": "А123ВС77",
            "enterprise_id": 1,
            "manager_user_ids": [10],
            "color": "green",
        },
    )

    await bus.publish(VEHICLE_EVENTS_TOPIC, source_event, key="42")

    assert telegram_sender.messages == [
        (9001, "Автомобиль А123ВС77: обновлен."),
    ]
    audit_events = await fetch_audit_events(integration_sessionmaker)
    assert len(audit_events) == 1
    stored = audit_events[0]
    assert stored.event_type == "notification.telegram.sent"
    assert stored.producer == "notification-service"
    assert stored.entity == "telegram_notification"
    assert stored.entity_id == "10"
    assert stored.correlation_id == source_event.event_id
    assert stored.payload["vehicle_id"] == 42
    assert stored.payload["vehicle_number"] == "А123ВС77"
    assert stored.payload["source_event_type"] == "vehicle.updated"
    assert stored.payload["result"] == "sent"


async def test_notification_service_does_not_emit_audit_without_telegram_session(
    integration_sessionmaker,
):
    await prepare_audit_tables(integration_sessionmaker)
    bus = InMemoryEventBus()
    telegram_sender = FakeTelegramSender()
    notification_service = VehicleEventNotificationService(
        telegram_session_registry=FakeTelegramSessionRegistry({}),
        telegram_sender=telegram_sender,
        audit_event_producer=bus,
    )

    async def store_audit_event(event: EventEnvelope) -> None:
        async with integration_sessionmaker() as session:
            await AuditEventService(AuditEventRepository(session)).handle(event)

    await bus.subscribe([VEHICLE_EVENTS_TOPIC], notification_service.handle)
    await bus.subscribe([AUDIT_EVENTS_TOPIC], store_audit_event)

    await bus.publish(
        VEHICLE_EVENTS_TOPIC,
        EventEnvelope.create(
            event_type="vehicle.deleted",
            producer="auto-parking-api",
            entity="vehicle",
            entity_id=42,
            payload={
                "vehicle_id": 42,
                "vehicle_number": "А123ВС77",
                "manager_user_ids": [10],
            },
        ),
        key="42",
    )

    assert telegram_sender.messages == []
    assert await fetch_audit_events(integration_sessionmaker) == []


async def test_audit_service_is_idempotent_for_duplicate_events(
    integration_sessionmaker,
):
    await prepare_audit_tables(integration_sessionmaker)
    event = EventEnvelope.create(
        event_type="vehicle.updated",
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=42,
        payload={
            "vehicle_id": 42,
            "vehicle_number": "А123ВС77",
            "color": "green",
        },
    )

    async with integration_sessionmaker() as session:
        service = AuditEventService(AuditEventRepository(session))
        await service.handle(event)
        await service.handle(event)

    audit_events = await fetch_audit_events(integration_sessionmaker)
    assert len(audit_events) == 1
    assert audit_events[0].event_id == event.event_id
    assert audit_events[0].event_type == "vehicle.updated"


async def test_notification_failure_is_published_and_stored_as_audit_event(
    integration_sessionmaker,
):
    await prepare_audit_tables(integration_sessionmaker)
    bus = InMemoryEventBus()
    telegram_sender = FakeTelegramSender(result=False)
    notification_service = VehicleEventNotificationService(
        telegram_session_registry=FakeTelegramSessionRegistry({10: 9001}),
        telegram_sender=telegram_sender,
        audit_event_producer=bus,
    )

    async def store_audit_event(event: EventEnvelope) -> None:
        async with integration_sessionmaker() as session:
            await AuditEventService(AuditEventRepository(session)).handle(event)

    await bus.subscribe([VEHICLE_EVENTS_TOPIC], notification_service.handle)
    await bus.subscribe([AUDIT_EVENTS_TOPIC], store_audit_event)

    source_event = EventEnvelope.create(
        event_type="vehicle.deleted",
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=42,
        payload={
            "vehicle_id": 42,
            "vehicle_number": "А123ВС77",
            "manager_user_ids": [10],
        },
    )

    await bus.publish(VEHICLE_EVENTS_TOPIC, source_event, key="42")

    assert telegram_sender.messages == [
        (9001, "Автомобиль А123ВС77: удален."),
    ]
    audit_events = await fetch_audit_events(integration_sessionmaker)
    assert len(audit_events) == 1
    stored = audit_events[0]
    assert stored.event_type == "notification.telegram.failed"
    assert stored.producer == "notification-service"
    assert stored.entity == "telegram_notification"
    assert stored.entity_id == "10"
    assert stored.correlation_id == source_event.event_id
    assert stored.payload["vehicle_id"] == 42
    assert stored.payload["vehicle_number"] == "А123ВС77"
    assert stored.payload["source_event_type"] == "vehicle.deleted"
    assert stored.payload["result"] == "failed"
