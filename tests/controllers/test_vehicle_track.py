import json
from types import SimpleNamespace

import pytest

from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.filter import EnterpriseFilter
from tests.conftest import (
    set_actor_override,
    set_enterprise_service_override,
    set_vehicle_service_override,
    set_vehicle_track_service_override,
    set_visible_ids_override,
)

pytestmark = pytest.mark.asyncio


def make_vehicle_stub(vehicle_id: int = 1, enterprise_id: int = 10):
    return SimpleNamespace(
        id=vehicle_id,
        enterprise_id=enterprise_id,
    )


def make_json_payload() -> str:
    return json.dumps(
        [
            {
                "id": 1,
                "trip_id": None,
                "recorded_at_utc": "2026-04-10T08:00:00Z",
                "recorded_at_enterprise": "2026-04-10T11:00:00+03:00",
                "latitude": 55.75,
                "longitude": 37.61,
            }
        ]
    )


def make_geojson_payload() -> str:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [37.61, 55.75],
                    },
                    "properties": {
                        "vehicle_id": 1,
                        "recorded_at_utc": "2026-04-10T08:00:00+00:00",
                        "recorded_at_enterprise": "2026-04-10T11:00:00+03:00",
                        "enterprise_timezone": "Europe/Moscow",
                    },
                }
            ],
        }
    )


async def test_get_vehicle_track_json_success(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_enterprise_service_override(overrides, enterprise_service_mock)
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    vehicle = make_vehicle_stub(vehicle_id=1, enterprise_id=10)
    vehicle_service_mock.get_by_id.return_value = vehicle
    enterprise_service_mock.get.return_value = [
        SimpleNamespace(id=10, timezone="Europe/Moscow")
    ]
    vehicle_track_service_mock.get_payload.return_value = make_json_payload()

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-10T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "json",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["id"] == 1
    assert body[0]["latitude"] == 55.75
    assert body[0]["longitude"] == 37.61
    assert body[0]["recorded_at_utc"] == "2026-04-10T08:00:00Z"
    assert body[0]["recorded_at_enterprise"] == "2026-04-10T11:00:00+03:00"

    vehicle_track_service_mock.get_payload.assert_awaited_once()
    enterprise_filter = enterprise_service_mock.get.await_args.args[0]
    assert isinstance(enterprise_filter, EnterpriseFilter)
    assert enterprise_filter.ids == [10]
    assert enterprise_filter.load_relations is False


async def test_get_vehicle_track_geojson_success(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_enterprise_service_override(overrides, enterprise_service_mock)
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    vehicle = make_vehicle_stub(vehicle_id=1, enterprise_id=10)
    vehicle_service_mock.get_by_id.return_value = vehicle
    enterprise_service_mock.get.return_value = [
        SimpleNamespace(id=10, timezone="Europe/Moscow")
    ]
    vehicle_track_service_mock.get_payload.return_value = make_geojson_payload()

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-10T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "geojson",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1
    assert body["features"][0]["geometry"]["type"] == "Point"
    assert body["features"][0]["geometry"]["coordinates"] == [37.61, 55.75]


async def test_get_vehicle_track_returns_404_when_vehicle_not_found(
    client,
    overrides,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    vehicle_service_mock.get_by_id.return_value = None

    response = await client.get(
        "/api/vehicles/999/track",
        params={
            "date_from": "2026-04-10T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "json",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Vehicle not found"


async def test_get_vehicle_track_returns_403_when_vehicle_not_visible(
    client,
    overrides,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {20})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    vehicle = make_vehicle_stub(vehicle_id=1, enterprise_id=10)
    vehicle_service_mock.get_by_id.return_value = vehicle

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-10T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "json",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


async def test_get_vehicle_track_returns_400_when_date_range_invalid(
    client,
    overrides,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-11T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "json",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "date_to must be >= date_from"

    vehicle_track_service_mock.get_payload.assert_not_called()


async def test_get_vehicle_track_returns_422_for_naive_datetime(
    client,
    overrides,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-10T00:00:00",
            "date_to": "2026-04-10T23:59:59",
            "format": "json",
        },
    )

    assert response.status_code in {400, 422}


async def test_get_vehicle_track_json_returns_empty_list_when_no_points(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_enterprise_service_override(overrides, enterprise_service_mock)
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    vehicle = make_vehicle_stub(vehicle_id=1, enterprise_id=10)
    vehicle_service_mock.get_by_id.return_value = vehicle
    enterprise_service_mock.get.return_value = [
        SimpleNamespace(id=10, timezone="Europe/Moscow")
    ]
    vehicle_track_service_mock.get_payload.return_value = "[]"

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-10T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "json",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_get_vehicle_track_geojson_returns_empty_feature_collection_when_no_points(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
    vehicle_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_enterprise_service_override(overrides, enterprise_service_mock)
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_vehicle_track_service_override(overrides, vehicle_track_service_mock)

    vehicle = make_vehicle_stub(vehicle_id=1, enterprise_id=10)
    vehicle_service_mock.get_by_id.return_value = vehicle
    enterprise_service_mock.get.return_value = [
        SimpleNamespace(id=10, timezone="Europe/Moscow")
    ]
    vehicle_track_service_mock.get_payload.return_value = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [],
        }
    )

    response = await client.get(
        "/api/vehicles/1/track",
        params={
            "date_from": "2026-04-10T00:00:00+03:00",
            "date_to": "2026-04-10T23:59:59+03:00",
            "format": "geojson",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "type": "FeatureCollection",
        "features": [],
    }
