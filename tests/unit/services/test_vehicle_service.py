from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.core.domain.models import VehicleModel
from auto_parking.filter import VehicleFilter
from auto_parking.service.vehicle import VehicleService

pytestmark = pytest.mark.asyncio


def vehicle_orm(**overrides):
    data = {
        "id": 1,
        "price": 1000,
        "mileage": 500,
        "vehicle_number": "А123ВС77",
        "owners_count": 1,
        "accident_number": 0,
        "manufacture_year": 2020,
        "model_id": 2,
        "color": "black",
        "enterprise_id": 10,
        "drivers": [SimpleNamespace(id=11)],
        "active_driver_id": 11,
        "purchased_at_utc": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        "enterprise": SimpleNamespace(timezone="Europe/Moscow"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


async def test_vehicle_service_maps_repo_results_to_domain_models():
    repo = AsyncMock()
    repo.get.return_value = [vehicle_orm()]
    service = VehicleService(repo)

    result = await service.get(VehicleFilter(enterprise_ids=[10]))

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].drivers == [11]
    assert result[0].enterprise_timezone == "Europe/Moscow"
    repo.get.assert_awaited_once()


async def test_vehicle_service_create_persists_domain_model():
    repo = AsyncMock()
    repo.create.return_value = vehicle_orm()
    service = VehicleService(repo)

    await service.create(
        VehicleModel(
            id=None,
            price=1000,
            mileage=500,
            vehicle_number="А123ВС77",
            owners_count=1,
            accident_number=0,
            manufacture_year=2020,
            model_id=2,
            enterprise_id=10,
            color="black",
            purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
    )

    data = repo.create.await_args.args[0]
    assert data["purchased_at_utc"] == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


async def test_vehicle_service_update_persists_domain_model():
    repo = AsyncMock()
    repo.update.return_value = vehicle_orm()
    service = VehicleService(repo)

    await service.update(
        1,
        VehicleModel(
            id=1,
            price=1000,
            mileage=500,
            vehicle_number="А123ВС77",
            owners_count=1,
            accident_number=0,
            manufacture_year=2020,
            model_id=2,
            enterprise_id=10,
            color="black",
            active_driver_id=None,
            purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        ),
    )

    data = repo.update.await_args.args[1]
    assert data["purchased_at_utc"] == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert data["active_driver_id"] is None
