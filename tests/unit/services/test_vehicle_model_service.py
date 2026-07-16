from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.app.service.vehicle_model import VehicleModelService

pytestmark = pytest.mark.asyncio


def model_orm(model_id: int = 2):
    return SimpleNamespace(
        id=model_id,
        name="Sedan",
        type="car",
        horse_powers=150,
        seats_number=5,
        fuel_capacity_liters=60,
    )


async def test_vehicle_model_service_get_all_maps_domain_models():
    repo = AsyncMock()
    repo.get_all.return_value = [model_orm()]
    service = VehicleModelService(repo)

    result = await service.get_all()

    assert len(result) == 1
    assert result[0].id == 2
    assert result[0].name == "Sedan"


async def test_vehicle_model_service_get_by_id_returns_none_when_missing():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = VehicleModelService(repo)

    result = await service.get_by_id(999)

    assert result is None
