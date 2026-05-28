from datetime import datetime
from types import SimpleNamespace

import pytest

from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.core.domain.models import TripModel, TripPointModel
from tests.conftest import (
    set_actor_override,
    set_trip_service_override,
    set_vehicle_service_override,
    set_visible_ids_override,
)

pytestmark = pytest.mark.asyncio


def make_vehicle_stub(vehicle_id: int = 3213, enterprise_id: int = 10):
    return SimpleNamespace(
        id=vehicle_id,
        enterprise_id=enterprise_id,
    )


def make_trip_stub(
    *,
    trip_id: int = 6,
    vehicle_id: int = 3213,
    enterprise_timezone: str = "America/Chicago",
    start_point_id: int = 64446,
    end_point_id: int = 64455,
):
    return TripModel(
        id=trip_id,
        vehicle_id=vehicle_id,
        started_at_utc=datetime.fromisoformat("2026-04-21T11:35:56.802506+00:00"),
        ended_at_utc=datetime.fromisoformat("2026-04-21T11:36:42.072286+00:00"),
        start_point_id=start_point_id,
        end_point_id=end_point_id,
        started_at_enterprise=datetime.fromisoformat("2026-04-21T06:35:56.802506-05:00"),
        ended_at_enterprise=datetime.fromisoformat("2026-04-21T06:36:42.072286-05:00"),
        enterprise_timezone=enterprise_timezone,
        start_point=TripPointModel(
            id=start_point_id,
            recorded_at_utc=datetime.fromisoformat("2026-04-21T11:35:56.802506+00:00"),
            recorded_at_enterprise=datetime.fromisoformat("2026-04-21T06:35:56.802506-05:00"),
            latitude=29.932136117862218,
            longitude=-90.05673157637868,
            address=None,
        ),
        end_point=TripPointModel(
            id=end_point_id,
            recorded_at_utc=datetime.fromisoformat("2026-04-21T11:36:42.072286+00:00"),
            recorded_at_enterprise=datetime.fromisoformat("2026-04-21T06:36:42.072286-05:00"),
            latitude=29.927131522589693,
            longitude=-90.05492833725192,
            address=None,
        ),
    )


async def test_get_vehicle_trips_success(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = make_vehicle_stub(
        vehicle_id=3213,
        enterprise_id=10,
    )
    trip_service_mock.get_vehicle_trips_in_range.return_value = [
        make_trip_stub(trip_id=6),
        make_trip_stub(trip_id=7, start_point_id=64456, end_point_id=64470),
    ]

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-21T11:35:00+00:00",
            "date_to": "2026-04-21T11:41:00+00:00",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert isinstance(body, list)
    assert len(body) == 2

    assert body[0]["id"] == 6
    assert body[0]["vehicle_id"] == 3213
    assert body[0]["enterprise_timezone"] == "America/Chicago"
    assert body[0]["start_point"]["id"] == 64446
    assert body[0]["start_point"]["address"] is None
    assert body[0]["end_point"]["id"] == 64455

    assert body[1]["id"] == 7
    assert body[1]["start_point"]["id"] == 64456
    assert body[1]["end_point"]["id"] == 64470

    vehicle_service_mock.get_by_id.assert_awaited_once_with(3213)
    trip_service_mock.get_vehicle_trips_in_range.assert_awaited_once_with(
        vehicle_id=3213,
        date_from=datetime.fromisoformat("2026-04-21T11:35:00+00:00"),
        date_to=datetime.fromisoformat("2026-04-21T11:41:00+00:00"),
        include_addresses=True,
    )


async def test_get_vehicle_trips_can_skip_addresses(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = make_vehicle_stub(
        vehicle_id=3213,
        enterprise_id=10,
    )
    trip_service_mock.get_vehicle_trips_in_range.return_value = []

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-21T11:35:00+00:00",
            "date_to": "2026-04-21T11:41:00+00:00",
            "include_addresses": "false",
        },
    )

    assert response.status_code == 200
    assert response.json() == []
    trip_service_mock.get_vehicle_trips_in_range.assert_awaited_once_with(
        vehicle_id=3213,
        date_from=datetime.fromisoformat("2026-04-21T11:35:00+00:00"),
        date_to=datetime.fromisoformat("2026-04-21T11:41:00+00:00"),
        include_addresses=False,
    )


async def test_get_vehicle_trips_returns_404_when_vehicle_not_found(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = None

    response = await client.get(
        "/api/vehicles/999/trips",
        params={
            "date_from": "2026-04-21T11:35:00+00:00",
            "date_to": "2026-04-21T11:41:00+00:00",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Vehicle not found"
    trip_service_mock.get_vehicle_trips_in_range.assert_not_called()


async def test_get_vehicle_trips_returns_403_when_vehicle_not_visible(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {20})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = make_vehicle_stub(
        vehicle_id=3213,
        enterprise_id=10,
    )

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-21T11:35:00+00:00",
            "date_to": "2026-04-21T11:41:00+00:00",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    trip_service_mock.get_vehicle_trips_in_range.assert_not_called()


async def test_get_vehicle_trips_returns_400_when_date_range_invalid(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-22T11:41:00+00:00",
            "date_to": "2026-04-21T11:35:00+00:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "date_to must be >= date_from"
    trip_service_mock.get_vehicle_trips_in_range.assert_not_called()


async def test_get_vehicle_trips_returns_422_or_400_for_naive_datetime(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = make_vehicle_stub(
        vehicle_id=3213,
        enterprise_id=10,
    )

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-21T11:35:00",
            "date_to": "2026-04-21T11:41:00",
        },
    )

    assert response.status_code in {400, 422}


async def test_get_vehicle_trips_returns_empty_list_when_no_trips(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = make_vehicle_stub(
        vehicle_id=3213,
        enterprise_id=10,
    )
    trip_service_mock.get_vehicle_trips_in_range.return_value = []

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-21T11:35:00+00:00",
            "date_to": "2026-04-21T11:41:00+00:00",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_get_vehicle_trips_returns_400_when_service_raises_value_error(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)

    vehicle_service_mock.get_by_id.return_value = make_vehicle_stub(
        vehicle_id=3213,
        enterprise_id=10,
    )
    trip_service_mock.get_vehicle_trips_in_range.side_effect = ValueError("Bad date range")

    response = await client.get(
        "/api/vehicles/3213/trips",
        params={
            "date_from": "2026-04-21T11:35:00+00:00",
            "date_to": "2026-04-21T11:41:00+00:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Bad date range"
