from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.core.domain.enums import ReportPeriod, ReportType
from auto_parking.core.domain.models import ReportCreateModel
from auto_parking.filter import TripFilter
from auto_parking.service.report import ReportService

pytestmark = pytest.mark.asyncio


def service_with_mocks():
    report_repo = AsyncMock()
    trip_repo = AsyncMock()
    vehicle_repo = AsyncMock()
    return ReportService(report_repo, trip_repo, vehicle_repo), report_repo, trip_repo, vehicle_repo


def payload(vehicle_id: int | None = 1) -> ReportCreateModel:
    return ReportCreateModel(
        name="Mileage",
        report_type=ReportType.vehicle_mileage,
        period=ReportPeriod.day,
        date_from=datetime(2026, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 1, 2, tzinfo=UTC),
        enterprise_id=10,
        vehicle_id=vehicle_id,
        params_json={},
    )


async def test_report_service_requires_vehicle_id_for_report_building():
    service, _, _, _ = service_with_mocks()

    with pytest.raises(ValueError, match="vehicle_id is required"):
        await service._build_result(payload(vehicle_id=None))


async def test_report_service_validates_vehicle_enterprise():
    service, _, _, vehicle_repo = service_with_mocks()
    vehicle_repo.get_by_id.return_value = SimpleNamespace(id=1, enterprise_id=20)

    with pytest.raises(ValueError, match="Vehicle does not belong"):
        await service._build_result(payload())


async def test_report_service_get_trips_uses_trip_filter():
    service, _, trip_repo, _ = service_with_mocks()
    trip_repo.get.return_value = []

    result = await service._get_trips(payload())

    assert result == []
    filter_obj = trip_repo.get.await_args.args[0]
    assert isinstance(filter_obj, TripFilter)
    assert filter_obj.vehicle_id == 1
    assert filter_obj.limit == 1000
    assert filter_obj.sort_by == "started_at_utc"
