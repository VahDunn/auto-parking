import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.infrastructure.db.models import VehicleModel

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def seed_vehicle_models(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> tuple[VehicleModel, VehicleModel]:
    async with sessionmaker() as session:
        solaris = VehicleModel(
            name="Solaris",
            type="sedan",
            horse_powers=123,
            seats_number=5,
            fuel_capacity_liters=50,
        )
        camry = VehicleModel(
            name="Camry",
            type="sedan",
            horse_powers=181,
            seats_number=5,
            fuel_capacity_liters=60,
        )
        session.add_all([solaris, camry])
        await session.commit()
        await session.refresh(solaris)
        await session.refresh(camry)
        return solaris, camry


async def test_vehicle_model_endpoints_read_models_from_database(
    integration_client,
    integration_sessionmaker,
):
    solaris, camry = await seed_vehicle_models(integration_sessionmaker)

    list_response = await integration_client.get("/api/vehicle-models")
    assert list_response.status_code == 200
    assert [model["name"] for model in list_response.json()] == ["Solaris", "Camry"]

    by_id_response = await integration_client.get(f"/api/vehicle-models/{solaris.id}")
    assert by_id_response.status_code == 200
    assert by_id_response.json() == {
        "id": solaris.id,
        "name": "Solaris",
        "type": "sedan",
        "horse_powers": 123,
        "seats_number": 5,
        "fuel_capacity_liters": 50,
    }

    by_name_response = await integration_client.get("/api/vehicle-models/by-name/Camry")
    assert by_name_response.status_code == 200
    assert by_name_response.json()["id"] == camry.id

    missing_response = await integration_client.get("/api/vehicle-models/999999")
    assert missing_response.status_code == 404
