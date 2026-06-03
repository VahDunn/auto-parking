import pytest

from auto_parking.core.domain.models import VehicleModelInfo
from tests.conftest import set_vehicle_model_service_override

pytestmark = pytest.mark.asyncio


async def test_vehicle_models_list_and_detail(client, overrides, vehicle_model_service_mock):
    set_vehicle_model_service_override(overrides, vehicle_model_service_mock)
    model = VehicleModelInfo(
        id=2,
        name="Sedan",
        type="car",
        horse_powers=150,
        seats_number=5,
        fuel_capacity_liters=60,
    )
    vehicle_model_service_mock.get_all.return_value = [model]
    vehicle_model_service_mock.get_by_id.return_value = model

    list_response = await client.get("/api/vehicle-models")
    detail_response = await client.get("/api/vehicle-models/2")

    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "Sedan"
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == 2


async def test_vehicle_model_detail_returns_404(client, overrides, vehicle_model_service_mock):
    set_vehicle_model_service_override(overrides, vehicle_model_service_mock)
    vehicle_model_service_mock.get_by_id.return_value = None

    response = await client.get("/api/vehicle-models/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Vehicle model not found"


async def test_vehicle_model_by_name_success(client, overrides, vehicle_model_service_mock):
    set_vehicle_model_service_override(overrides, vehicle_model_service_mock)
    model = VehicleModelInfo(
        id=2,
        name="Sedan",
        type="car",
        horse_powers=150,
        seats_number=5,
        fuel_capacity_liters=60,
    )
    vehicle_model_service_mock.get_by_name.return_value = model

    response = await client.get("/api/vehicle-models/by-name/Sedan")

    assert response.status_code == 200
    assert response.json()["name"] == "Sedan"
    vehicle_model_service_mock.get_by_name.assert_awaited_once_with("Sedan")
