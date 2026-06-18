import asyncio
from unittest.mock import AsyncMock

import pytest

from auto_parking.realtime.gps import GpsPointEvent, GpsRealtimeHub

pytestmark = pytest.mark.asyncio


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
