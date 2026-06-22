from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from auto_parking.core.domain.enums import TrackFormat, UserRole
from auto_parking.core.domain.models import TripTrackGroupModel, VehicleTrackPointModel
from auto_parking.filter import VehicleFilter
from tests.conftest import (
    set_actor_override,
    set_enterprise_service_override,
    set_export_service_override,
    set_gpx_import_service_override,
    set_trip_service_override,
    set_trip_track_service_override,
    set_vehicle_service_override,
    set_visible_ids_override,
)
from tests.factories import trip_model, vehicle_model

pytestmark = pytest.mark.asyncio


async def test_get_vehicles_builds_filter_and_respects_visibility(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10, 20})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_enterprise_service_override(overrides, enterprise_service_mock)
    vehicle = vehicle_model(enterprise_id=10)
    vehicle.enterprise_timezone = "Europe/Moscow"
    vehicle_service_mock.get.return_value = [vehicle]

    response = await client.get(
        "/api/vehicles",
        params={
            "id": "1,2",
            "vehicle_number_prefix": "А123",
            "enterprise_ids": "10,30",
            "driver_id": 11,
            "limit": 10,
            "offset": 5,
            "sort_by": "id",
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
    assert response.json()[0]["enterprise_timezone"] == "Europe/Moscow"

    filter_obj = vehicle_service_mock.get.await_args.args[0]
    assert isinstance(filter_obj, VehicleFilter)
    assert filter_obj.id == [1, 2]
    assert filter_obj.vehicle_number_prefix == "А123"
    assert filter_obj.enterprise_ids == [10]
    assert filter_obj.driver_id == 11
    assert filter_obj.limit == 10
    assert filter_obj.offset == 5
    assert filter_obj.sort_by == "id"
    enterprise_service_mock.get.assert_not_called()


async def test_vehicle_crud_success(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_enterprise_service_override(overrides, enterprise_service_mock)
    enterprise_service_mock.get.return_value = [
        SimpleNamespace(id=10, timezone="Europe/Moscow")
    ]
    vehicle = vehicle_model()
    vehicle_service_mock.get_by_id.return_value = vehicle
    vehicle_service_mock.create.return_value = vehicle
    vehicle_service_mock.update.return_value = vehicle_model(vehicle_id=1, enterprise_id=10)
    vehicle_service_mock.delete.return_value = True

    post_payload = {
        "price": 1000,
        "mileage": 500,
        "vehicle_number": " а123вс77 ",
        "owners_count": 1,
        "accident_number": 0,
        "manufacture_year": 2020,
        "model_id": 2,
        "enterprise_id": 10,
        "color": "black",
        "purchased_at": "2026-01-01T12:00:00+03:00",
    }

    create_response = await client.post("/api/vehicles", json=post_payload)
    detail_response = await client.get("/api/vehicles/1")
    update_response = await client.patch("/api/vehicles/1", json={"price": 2000})
    delete_response = await client.delete("/api/vehicles/1")

    assert create_response.status_code == 201
    assert detail_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 204
    created_vehicle = vehicle_service_mock.create.await_args.args[0]
    assert created_vehicle.vehicle_number == "А123ВС77"


async def test_vehicle_create_forbidden_when_enterprise_not_visible(
    client,
    overrides,
    vehicle_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {20})
    set_vehicle_service_override(overrides, vehicle_service_mock)

    response = await client.post(
        "/api/vehicles",
        json={
            "price": 1000,
            "mileage": 500,
            "vehicle_number": "А123ВС77",
            "owners_count": 1,
            "accident_number": 0,
            "manufacture_year": 2020,
            "model_id": 2,
            "enterprise_id": 10,
            "color": "black",
            "purchased_at": "2026-01-01T12:00:00+03:00",
        },
    )

    assert response.status_code == 403
    vehicle_service_mock.create.assert_not_called()


async def test_export_vehicle_trips_returns_attachment(
    client,
    overrides,
    vehicle_service_mock,
    export_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_export_service_override(overrides, export_service_mock)
    vehicle_service_mock.get_by_id.return_value = vehicle_model()
    export_service_mock.export_vehicle_trips.return_value = '{"trips": []}'

    response = await client.get(
        "/api/vehicles/1/export-trips",
        params={
            "date_from": "2026-01-01T00:00:00+00:00",
            "date_to": "2026-01-02T00:00:00+00:00",
            "format": "json",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert 'filename="vehicle_1_trips_export.json"' in response.headers["content-disposition"]


async def test_import_vehicle_trip_gpx_success(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
    gpx_import_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)
    set_gpx_import_service_override(overrides, gpx_import_service_mock)
    vehicle_service_mock.get_by_id.return_value = vehicle_model()
    gpx_import_service_mock.import_vehicle_trip.return_value = 7
    trip_service_mock.get_by_id.return_value = trip_model()

    response = await client.post(
        "/api/vehicles/1/trips/import-gpx",
        files={"file": ("track.gpx", b"<gpx></gpx>", "application/gpx+xml")},
    )

    assert response.status_code == 201
    assert response.json()["id"] == 7


async def test_import_vehicle_trip_gpx_rejects_non_gpx(
    client,
    overrides,
    vehicle_service_mock,
    trip_service_mock,
    gpx_import_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_service_override(overrides, trip_service_mock)
    set_gpx_import_service_override(overrides, gpx_import_service_mock)
    vehicle_service_mock.get_by_id.return_value = vehicle_model()

    response = await client.post(
        "/api/vehicles/1/trips/import-gpx",
        files={"file": ("track.txt", b"not gpx", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .gpx files are supported"


async def test_get_vehicle_track_by_trips_success(
    client,
    overrides,
    enterprise_service_mock,
    vehicle_service_mock,
    trip_track_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_enterprise_service_override(overrides, enterprise_service_mock)
    set_vehicle_service_override(overrides, vehicle_service_mock)
    set_trip_track_service_override(overrides, trip_track_service_mock)
    vehicle_service_mock.get_by_id.return_value = vehicle_model()
    enterprise_service_mock.get.return_value = [
        SimpleNamespace(id=10, timezone="Europe/Moscow")
    ]
    point = VehicleTrackPointModel(
        id=1,
        recorded_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        recorded_at_enterprise=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        latitude=55.75,
        longitude=37.61,
    )
    trip_track_service_mock.get_grouped_track.return_value = [
        TripTrackGroupModel(
            trip_id=7,
            vehicle_id=1,
            started_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            ended_at_utc=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            started_at_enterprise=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            ended_at_enterprise=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            enterprise_timezone="UTC",
            points=[point],
            track=None,
        )
    ]

    response = await client.get(
        "/api/vehicles/1/track-by-trips",
        params={
            "date_from": "2026-01-01T00:00:00+00:00",
            "date_to": "2026-01-02T00:00:00+00:00",
            "format": "json",
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["trip_id"] == 7
    assert response.json()[0]["points"][0]["latitude"] == 55.75
    trip_track_service_mock.get_grouped_track.assert_awaited_once_with(
        vehicle_id=1,
        date_from=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        date_to=datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
        format=TrackFormat.json,
        enterprise_timezone="Europe/Moscow",
    )
