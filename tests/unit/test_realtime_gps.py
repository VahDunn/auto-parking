import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from auto_parking.infrastructure.realtime.gps import (
    GPS_EVENT_TYPE,
    GpsPointEvent,
    GpsRealtimeHub,
    publish_gps_point,
)
from event_bus.contracts import GPS_EVENTS_TOPIC, EventEnvelope

pytestmark = pytest.mark.asyncio


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


def gps_payload(**overrides):
    payload = {
        "vehicle_id": 1,
        "vehicle_number": "А123ВС77",
        "enterprise_id": 10,
        "recorded_at_utc": "2026-06-11T10:00:00+00:00",
        "latitude": 55.75,
        "longitude": 37.61,
    }
    payload.update(overrides)
    return payload


async def test_publish_gps_point_sends_event_to_gps_topic():
    producer = FakeEventProducer()

    await publish_gps_point(
        producer,
        vehicle_id=1,
        vehicle_number="А123ВС77",
        enterprise_id=10,
        recorded_at_utc=datetime(2026, 6, 11, 10, 0, tzinfo=UTC),
        latitude=55.75,
        longitude=37.61,
    )

    topic, event, key = producer.messages[0]
    assert topic == GPS_EVENTS_TOPIC
    assert key == "1"
    assert event.event_type == GPS_EVENT_TYPE
    assert event.entity == "vehicle"
    assert event.entity_id == 1
    assert event.payload["vehicle_number"] == "А123ВС77"


async def test_reactive_pipeline_filters_invalid_points_and_duplicates():
    hub = GpsRealtimeHub()
    websocket = AsyncMock()
    hub._connections[websocket] = None

    hub.emit(gps_payload(latitude=100))
    hub.emit(gps_payload())
    hub.emit(gps_payload())
    await asyncio.sleep(0)

    websocket.send_json.assert_awaited_once()
    point = websocket.send_json.await_args.args[0]["point"]
    assert point["vehicle_id"] == 1
    assert point["vehicle_number"] == "А123ВС77"


async def test_handle_event_emits_valid_gps_payloads_only():
    hub = GpsRealtimeHub()
    websocket = AsyncMock()
    hub._connections[websocket] = None

    await hub.handle_event(
        EventEnvelope.create(
            event_type="driver.updated",
            producer="test",
            entity="driver",
            entity_id=1,
            payload=gps_payload(),
        )
    )
    await hub.handle_event(
        EventEnvelope.create(
            event_type=GPS_EVENT_TYPE,
            producer="test",
            entity="vehicle",
            entity_id=1,
            payload=gps_payload(),
        )
    )
    await asyncio.sleep(0)

    websocket.send_json.assert_awaited_once()


async def test_broadcast_respects_visible_enterprises():
    hub = GpsRealtimeHub()
    allowed = AsyncMock()
    forbidden = AsyncMock()
    admin = AsyncMock()
    hub._connections = {
        allowed: {10},
        forbidden: {20},
        admin: None,
    }

    await hub._broadcast(GpsPointEvent.from_payload(gps_payload()))

    allowed.send_json.assert_awaited_once()
    forbidden.send_json.assert_not_awaited()
    admin.send_json.assert_awaited_once()
