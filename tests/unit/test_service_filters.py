from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.api.schemas.vehicle_track import TrackFormat
from auto_parking.filter import TripFilter, VehicleFilter
from auto_parking.service.export import ExportService
from auto_parking.service.gpx_import import GpxImportService
from auto_parking.service.trip import TripService
from auto_parking.service.trip_track import TripTrackService

pytestmark = pytest.mark.asyncio


async def test_trip_service_uses_trip_filter_for_range_query():
    repo = AsyncMock()
    repo.get.return_value = []
    service = TripService(repo=repo)

    date_from = datetime(2026, 4, 21, 11, 35, tzinfo=UTC)
    date_to = datetime(2026, 4, 21, 11, 41, tzinfo=UTC)

    result = await service.get_vehicle_trips_in_range(
        vehicle_id=3213,
        date_from=date_from,
        date_to=date_to,
    )

    assert result == []
    repo.get.assert_awaited_once()

    filter_obj = repo.get.await_args.args[0]
    assert isinstance(filter_obj, TripFilter)
    assert filter_obj.vehicle_id == 3213
    assert filter_obj.started_from == date_from
    assert filter_obj.ended_to == date_to
    assert filter_obj.limit is None
    assert filter_obj.offset is None


async def test_trip_track_service_uses_trip_filter_for_grouped_track():
    vehicle_repo = AsyncMock()
    trip_repo = AsyncMock()
    track_repo = AsyncMock()
    service = TripTrackService(
        vehicle_repo=vehicle_repo,
        trip_repo=trip_repo,
        track_repo=track_repo,
    )

    vehicle_repo.get_by_id.return_value = SimpleNamespace(
        id=3213,
        enterprise=SimpleNamespace(timezone="UTC"),
    )
    trip_repo.get.return_value = []

    date_from = datetime(2026, 4, 21, 11, 35, tzinfo=UTC)
    date_to = datetime(2026, 4, 21, 11, 41, tzinfo=UTC)

    result = await service.get_grouped_track(
        vehicle_id=3213,
        date_from=date_from,
        date_to=date_to,
        format=TrackFormat.json,
    )

    assert result == []
    trip_repo.get.assert_awaited_once()
    track_repo.get_points.assert_not_called()

    filter_obj = trip_repo.get.await_args.args[0]
    assert isinstance(filter_obj, TripFilter)
    assert filter_obj.vehicle_id == 3213
    assert filter_obj.started_from == date_from
    assert filter_obj.ended_to == date_to
    assert filter_obj.limit is None
    assert filter_obj.offset is None


async def test_export_service_uses_vehicle_filter_for_enterprise_vehicles():
    enterprise_repo = AsyncMock()
    vehicle_repo = AsyncMock()
    driver_repo = AsyncMock()
    trip_repo = AsyncMock()
    track_repo = AsyncMock()
    service = ExportService(
        enterprise_repo=enterprise_repo,
        vehicle_repo=vehicle_repo,
        driver_repo=driver_repo,
        trip_repo=trip_repo,
        track_repo=track_repo,
    )

    enterprise_repo.get_by_id.return_value = SimpleNamespace(
        id=10,
        name="Enterprise",
        settlement="Moscow",
        timezone="Europe/Moscow",
    )
    vehicle_repo.get.return_value = []

    result = await service.export_enterprise_vehicles(enterprise_id=10)

    assert '"vehicles": []' in result
    vehicle_repo.get.assert_awaited_once()

    filter_obj = vehicle_repo.get.await_args.args[0]
    assert isinstance(filter_obj, VehicleFilter)
    assert filter_obj.enterprise_ids == [10]
    assert filter_obj.limit is None
    assert filter_obj.offset is None


async def test_gpx_import_service_uses_standard_trip_filter_for_overlap_candidates():
    vehicle_repo = AsyncMock()
    trip_repo = AsyncMock()
    track_repo = AsyncMock()
    service = GpxImportService(
        vehicle_repo=vehicle_repo,
        trip_repo=trip_repo,
        track_repo=track_repo,
    )

    vehicle_repo.get_by_id.return_value = SimpleNamespace(id=3213)
    trip_repo.get.return_value = []
    trip_repo.create.return_value = SimpleNamespace(id=7)
    track_repo.get_points_by_intervals.return_value = []
    track_repo.create_points_bulk.return_value = [
        SimpleNamespace(id=101),
        SimpleNamespace(id=102),
    ]

    raw_gpx = b"""
    <gpx>
      <trk><trkseg>
        <trkpt lat="55.75" lon="37.61"><time>2026-04-21T11:35:00Z</time></trkpt>
        <trkpt lat="55.76" lon="37.62"><time>2026-04-21T11:41:00Z</time></trkpt>
      </trkseg></trk>
    </gpx>
    """

    result = await service.import_vehicle_trip(vehicle_id=3213, raw_gpx=raw_gpx)

    assert result == 7
    trip_repo.get.assert_awaited_once()

    filter_obj = trip_repo.get.await_args.args[0]
    assert isinstance(filter_obj, TripFilter)
    assert filter_obj.vehicle_id == 3213
    assert filter_obj.started_to == datetime(2026, 4, 21, 11, 41, tzinfo=UTC)
    assert filter_obj.limit is None
    assert filter_obj.offset is None


async def test_gpx_import_service_detects_trip_overlap_in_service_layer():
    assert GpxImportService._trip_overlaps(
        trip_started_at_utc=datetime(2026, 4, 21, 11, 30, tzinfo=UTC),
        trip_ended_at_utc=datetime(2026, 4, 21, 11, 36, tzinfo=UTC),
        started_at_utc=datetime(2026, 4, 21, 11, 35, tzinfo=UTC),
        ended_at_utc=datetime(2026, 4, 21, 11, 41, tzinfo=UTC),
    )
    assert not GpxImportService._trip_overlaps(
        trip_started_at_utc=datetime(2026, 4, 21, 11, 10, tzinfo=UTC),
        trip_ended_at_utc=datetime(2026, 4, 21, 11, 20, tzinfo=UTC),
        started_at_utc=datetime(2026, 4, 21, 11, 35, tzinfo=UTC),
        ended_at_utc=datetime(2026, 4, 21, 11, 41, tzinfo=UTC),
    )
