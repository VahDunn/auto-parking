from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.app.filter import DriverFilter
from auto_parking.app.service.driver import DriverService

pytestmark = pytest.mark.asyncio


def driver_orm(active_vehicle=None):
    return SimpleNamespace(
        id=11,
        name="Driver",
        salary_rub=100000,
        enterprise_id=10,
        active_vehicle=active_vehicle,
        vehicles=[SimpleNamespace(id=1), SimpleNamespace(id=2)],
    )


async def test_driver_service_get_maps_drivers_to_domain_models():
    repo = AsyncMock()
    repo.get.return_value = [driver_orm(active_vehicle=SimpleNamespace(id=1))]
    service = DriverService(repo)

    result = await service.get(DriverFilter(enterprise_ids=[10]))

    assert len(result) == 1
    assert result[0].id == 11
    assert result[0].vehicles == [1, 2]
    assert result[0].active_vehicle_id == 1


async def test_driver_service_get_by_id_returns_none_when_missing():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = DriverService(repo)

    result = await service.get_by_id(999)

    assert result is None
