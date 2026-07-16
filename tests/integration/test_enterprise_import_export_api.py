import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.infrastructure.db.models import Enterprise, Trip, Vehicle, VehicleGpsPoint
from auto_parking.infrastructure.db.models.vehicle_model import VehicleModel as VehicleModelOrm

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def seed_vehicle_model(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> VehicleModelOrm:
    async with sessionmaker() as session:
        model = VehicleModelOrm(
            name="Solaris",
            type="sedan",
            horse_powers=123,
            seats_number=5,
            fuel_capacity_liters=50,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model


async def test_enterprise_json_import_and_vehicle_export_roundtrip(
    integration_client,
    integration_sessionmaker,
):
    model = await seed_vehicle_model(integration_sessionmaker)
    payload = {
        "enterprise": {
            "name": "Imported enterprise",
            "settlement": "Moscow",
            "timezone": "Europe/Moscow",
        },
        "vehicles": [
            {
                "price": 1_700_000,
                "mileage": 4_200,
                "vehicle_number": "А777АА77",
                "owners_count": 1,
                "accident_number": 0,
                "manufacture_year": 2024,
                "model_id": model.id,
                "color": "blue",
                "purchased_at_utc": "2026-06-01T09:00:00+00:00",
                "trips": [
                    {
                        "started_at_utc": "2026-06-01T10:00:00+00:00",
                        "ended_at_utc": "2026-06-01T10:05:00+00:00",
                        "points": [
                            {
                                "recorded_at_utc": "2026-06-01T10:00:00+00:00",
                                "latitude": 55.751244,
                                "longitude": 37.618423,
                            },
                            {
                                "recorded_at_utc": "2026-06-01T10:05:00+00:00",
                                "latitude": 55.752,
                                "longitude": 37.62,
                            },
                        ],
                    }
                ],
            }
        ],
    }

    import_response = await integration_client.post(
        "/api/enterprises/import",
        params={"format": "json"},
        files={
            "file": (
                "enterprise.json",
                json.dumps(payload).encode("utf-8"),
                "application/json",
            )
        },
    )

    assert import_response.status_code == 200
    imported = import_response.json()
    assert imported["imported_vehicles"] == 1
    assert imported["imported_trips"] == 1
    assert imported["imported_points"] == 2

    async with integration_sessionmaker() as session:
        vehicle_count = await session.scalar(select(func.count()).select_from(Vehicle))
        trip_count = await session.scalar(select(func.count()).select_from(Trip))
        point_count = await session.scalar(select(func.count()).select_from(VehicleGpsPoint))
        enterprise = await session.get(Enterprise, imported["enterprise_id"])

    assert vehicle_count == 1
    assert trip_count == 1
    assert point_count == 2
    assert enterprise is not None
    assert enterprise.name == "Imported enterprise"

    export_response = await integration_client.get(
        f"/api/enterprises/{imported['enterprise_id']}/export-vehicles",
        params={"format": "json"},
    )

    assert export_response.status_code == 200
    exported = export_response.json()
    assert exported["enterprise"]["name"] == "Imported enterprise"
    assert exported["vehicles"] == [
        {
            "id": exported["vehicles"][0]["id"],
            "price": 1_700_000,
            "mileage": 4_200,
            "vehicle_number": "А777АА77",
            "owners_count": 1,
            "accident_number": 0,
            "manufacture_year": 2024,
            "model_id": model.id,
            "enterprise_id": imported["enterprise_id"],
            "active_driver_id": None,
            "color": "blue",
            "purchased_at_utc": "2026-06-01T09:00:00+00:00",
        }
    ]
