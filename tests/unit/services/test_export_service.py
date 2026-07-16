import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.app.filter import TripFilter, VehicleTrackFilter
from auto_parking.app.service.export import ExportService

pytestmark = pytest.mark.asyncio


def _vehicle(vehicle_id: int, drivers=None):
    return SimpleNamespace(
        id=vehicle_id,
        price=1000,
        mileage=500,
        vehicle_number=f"A{vehicle_id:03d}AA77",
        owners_count=1,
        accident_number=0,
        manufacture_year=2020,
        model_id=2,
        enterprise_id=10,
        active_driver_id=None,
        color="black",
        purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        drivers=drivers or [],
    )


def _trip(trip_id: int, vehicle_id: int):
    return SimpleNamespace(
        id=trip_id,
        vehicle_id=vehicle_id,
        started_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        ended_at_utc=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        start_point_id=None,
        end_point_id=None,
    )


def _point(point_id: int, vehicle_id: int):
    return SimpleNamespace(
        id=point_id,
        vehicle_id=vehicle_id,
        recorded_at_utc=datetime(2026, 1, 1, 9, 30, tzinfo=UTC),
        latitude=55.75 + point_id,
        longitude=37.61 + point_id,
    )


def _service():
    enterprise_repo = AsyncMock()
    vehicle_repo = AsyncMock()
    driver_repo = AsyncMock()
    trip_repo = AsyncMock()
    track_repo = AsyncMock()

    enterprise_repo.get_by_id.return_value = SimpleNamespace(
        id=10,
        name="Enterprise",
        settlement="Moscow",
        timezone="Europe/Moscow",
    )

    return (
        ExportService(
            enterprise_repo=enterprise_repo,
            vehicle_repo=vehicle_repo,
            driver_repo=driver_repo,
            trip_repo=trip_repo,
            track_repo=track_repo,
        ),
        vehicle_repo,
        driver_repo,
        trip_repo,
        track_repo,
    )


async def test_enterprise_full_export_batches_trip_lookup_by_vehicle_ids():
    service, vehicle_repo, _driver_repo, trip_repo, track_repo = _service()
    vehicle_1 = _vehicle(1)
    vehicle_2 = _vehicle(2)
    vehicle_repo.get.return_value = [vehicle_1, vehicle_2]
    trip_repo.get.return_value = [_trip(101, 1), _trip(201, 2)]
    track_repo.get.return_value = [_point(1, 1), _point(2, 2)]

    content = await service.export_enterprise_full(
        enterprise_id=10,
        date_from=datetime(2026, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 1, 2, tzinfo=UTC),
    )

    data = json.loads(content)
    trip_filter = trip_repo.get.await_args.args[0]
    assert isinstance(trip_filter, TripFilter)
    assert trip_filter.vehicle_ids == [1, 2]
    assert trip_filter.vehicle_id is None
    assert trip_filter.load_relations is False
    trip_repo.get.assert_awaited_once()
    track_filter = track_repo.get.await_args.args[0]
    assert isinstance(track_filter, VehicleTrackFilter)
    assert track_filter.vehicle_ids == [1, 2]
    assert track_filter.vehicle_id is None
    assert track_filter.trip_started_from == datetime(2026, 1, 1, tzinfo=UTC)
    assert track_filter.trip_ended_to == datetime(2026, 1, 2, tzinfo=UTC)
    track_repo.get.assert_awaited_once()
    assert [vehicle["trips"][0]["id"] for vehicle in data["vehicles"]] == [101, 201]
    assert [vehicle["trips"][0]["points"][0]["latitude"] for vehicle in data["vehicles"]] == [
        56.75,
        57.75,
    ]


async def test_guid_dump_export_batches_trip_lookup_by_vehicle_ids():
    service, vehicle_repo, driver_repo, trip_repo, track_repo = _service()
    vehicle_1 = _vehicle(1)
    vehicle_2 = _vehicle(2)
    vehicle_repo.get.return_value = [vehicle_1, vehicle_2]
    driver_repo.get.return_value = [
        SimpleNamespace(id=11, name="Driver", salary_rub=100000, active_vehicle_id=1, vehicles=[]),
    ]
    trip_repo.get.return_value = [_trip(101, 1), _trip(201, 2)]
    track_repo.get.return_value = [_point(1, 1), _point(2, 2)]

    content = await service.export_enterprise_guid_dump(
        enterprise_id=10,
        date_from=datetime(2026, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 1, 2, tzinfo=UTC),
    )

    data = json.loads(content)
    trip_filter = trip_repo.get.await_args.args[0]
    assert isinstance(trip_filter, TripFilter)
    assert trip_filter.vehicle_ids == [1, 2]
    assert trip_filter.vehicle_id is None
    assert trip_filter.load_relations is False
    trip_repo.get.assert_awaited_once()
    track_filter = track_repo.get.await_args.args[0]
    assert isinstance(track_filter, VehicleTrackFilter)
    assert track_filter.vehicle_ids == [1, 2]
    assert track_filter.vehicle_id is None
    assert track_filter.trip_started_from == datetime(2026, 1, 1, tzinfo=UTC)
    assert track_filter.trip_ended_to == datetime(2026, 1, 2, tzinfo=UTC)
    track_repo.get.assert_awaited_once()
    assert [trip["source_id"] for trip in data["trips"]] == [101, 201]
    assert len(data["points"]) == 2
