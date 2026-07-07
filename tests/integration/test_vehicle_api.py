from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.db.models import Enterprise, OutboxEvent, Vehicle
from auto_parking.db.models.vehicle_model import VehicleModel as VehicleModelOrm
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.main import app as fastapi_app
from auto_parking.ports.events import AUDIT_EVENTS_TOPIC, VEHICLE_EVENTS_TOPIC
from auto_parking.repo.vehicle_track import VehicleTrackRepository
from auto_parking.service.outbox import OutboxDispatcher

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def seed_enterprise_and_model(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> tuple[Enterprise, VehicleModelOrm]:
    async with sessionmaker() as session:
        enterprise = Enterprise(
            name="Test enterprise",
            settlement="Moscow",
            timezone="Europe/Moscow",
        )
        model = VehicleModelOrm(
            name="Solaris",
            type="sedan",
            horse_powers=123,
            seats_number=5,
            fuel_capacity_liters=50,
        )
        session.add_all([enterprise, model])
        await session.commit()
        await session.refresh(enterprise)
        await session.refresh(model)
        return enterprise, model


async def seed_vehicle(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    enterprise: Enterprise,
    model: VehicleModelOrm,
    number: str,
) -> Vehicle:
    async with sessionmaker() as session:
        vehicle = Vehicle(
            price=1_500_000,
            mileage=12_000,
            vehicle_number=number,
            owners_count=1,
            accident_number=0,
            manufacture_year=2022,
            model_id=model.id,
            enterprise_id=enterprise.id,
            color="white",
        )
        session.add(vehicle)
        await session.commit()
        await session.refresh(vehicle)
        return vehicle


async def get_vehicle_from_db(
    sessionmaker: async_sessionmaker[AsyncSession],
    vehicle_id: int,
) -> Vehicle | None:
    async with sessionmaker() as session:
        result = await session.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
        return result.scalar_one_or_none()


async def get_outbox_events(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> list[OutboxEvent]:
    async with sessionmaker() as session:
        result = await session.execute(select(OutboxEvent).order_by(OutboxEvent.id))
        return list(result.scalars().all())


async def seed_track_points(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    vehicle_id: int,
    started_at: datetime,
) -> None:
    async with sessionmaker() as session:
        repo = VehicleTrackRepository(session)
        await repo.create_many(
            [
                {
                    "vehicle_id": vehicle_id,
                    "recorded_at_utc": started_at,
                    "latitude": 55.751244,
                    "longitude": 37.618423,
                },
                {
                    "vehicle_id": vehicle_id,
                    "recorded_at_utc": started_at + timedelta(minutes=5),
                    "latitude": 55.752,
                    "longitude": 37.62,
                },
                {
                    "vehicle_id": vehicle_id,
                    "recorded_at_utc": started_at + timedelta(hours=2),
                    "latitude": 55.9,
                    "longitude": 37.9,
                },
            ]
        )


async def test_vehicle_crud_persists_data_and_publishes_events_from_outbox(
    integration_client,
    integration_sessionmaker,
    captured_event_producer,
):
    enterprise, model = await seed_enterprise_and_model(integration_sessionmaker)

    create_response = await integration_client.post(
        "/api/vehicles",
        json={
            "price": 1_700_000,
            "mileage": 4_200,
            "vehicle_number": "а123вс77",
            "owners_count": 1,
            "accident_number": 0,
            "manufacture_year": 2024,
            "model_id": model.id,
            "enterprise_id": enterprise.id,
            "color": "blue",
            "purchased_at": "2026-06-01T12:00:00+03:00",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["vehicle_number"] == "А123ВС77"
    assert created["enterprise_timezone"] == "Europe/Moscow"

    persisted = await get_vehicle_from_db(integration_sessionmaker, created["id"])
    assert persisted is not None
    assert persisted.vehicle_number == "А123ВС77"
    assert persisted.color == "blue"

    list_response = await integration_client.get(
        "/api/vehicles",
        params={"vehicle_number_prefix": "А123"},
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    update_response = await integration_client.patch(
        f"/api/vehicles/{created['id']}",
        json={"color": "green"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["color"] == "green"

    updated = await get_vehicle_from_db(integration_sessionmaker, created["id"])
    assert updated is not None
    assert updated.color == "green"

    delete_response = await integration_client.delete(f"/api/vehicles/{created['id']}")
    assert delete_response.status_code == 204
    assert await get_vehicle_from_db(integration_sessionmaker, created["id"]) is None

    outbox_events = await get_outbox_events(integration_sessionmaker)
    assert captured_event_producer.published == []
    outbox_summary = [
        (event.topic, event.event_type, event.key, event.status) for event in outbox_events
    ]
    assert outbox_summary == [
        (VEHICLE_EVENTS_TOPIC, "vehicle.created", str(created["id"]), "pending"),
        (AUDIT_EVENTS_TOPIC, "vehicle.created", str(created["id"]), "pending"),
        (VEHICLE_EVENTS_TOPIC, "vehicle.updated", str(created["id"]), "pending"),
        (AUDIT_EVENTS_TOPIC, "vehicle.updated", str(created["id"]), "pending"),
        (VEHICLE_EVENTS_TOPIC, "vehicle.deleted", str(created["id"]), "pending"),
        (AUDIT_EVENTS_TOPIC, "vehicle.deleted", str(created["id"]), "pending"),
    ]

    dispatcher = OutboxDispatcher(
        sessionmaker=integration_sessionmaker,
        producer_factory=lambda: captured_event_producer,
        batch_size=10,
    )
    assert await dispatcher.dispatch_once() == 6

    published = captured_event_producer.published
    assert [(topic, event.event_type, key) for topic, event, key in published] == [
        (VEHICLE_EVENTS_TOPIC, "vehicle.created", str(created["id"])),
        (AUDIT_EVENTS_TOPIC, "vehicle.created", str(created["id"])),
        (VEHICLE_EVENTS_TOPIC, "vehicle.updated", str(created["id"])),
        (AUDIT_EVENTS_TOPIC, "vehicle.updated", str(created["id"])),
        (VEHICLE_EVENTS_TOPIC, "vehicle.deleted", str(created["id"])),
        (AUDIT_EVENTS_TOPIC, "vehicle.deleted", str(created["id"])),
    ]

    outbox_after_dispatch = await get_outbox_events(integration_sessionmaker)
    assert {event.status for event in outbox_after_dispatch} == {"published"}
    assert all(event.published_at is not None for event in outbox_after_dispatch)


async def test_outbox_keeps_vehicle_event_pending_when_publish_fails(
    integration_client,
    integration_sessionmaker,
):
    class FailingProducer:
        async def publish(self, topic, event, *, key=None):
            raise RuntimeError("kafka is down")

        async def close(self):
            return None

    enterprise, model = await seed_enterprise_and_model(integration_sessionmaker)

    create_response = await integration_client.post(
        "/api/vehicles",
        json={
            "price": 1_700_000,
            "mileage": 4_200,
            "vehicle_number": "а555вс77",
            "owners_count": 1,
            "accident_number": 0,
            "manufacture_year": 2024,
            "model_id": model.id,
            "enterprise_id": enterprise.id,
            "color": "blue",
            "purchased_at": "2026-06-01T12:00:00+03:00",
        },
    )
    assert create_response.status_code == 201

    dispatcher = OutboxDispatcher(
        sessionmaker=integration_sessionmaker,
        producer_factory=FailingProducer,
        batch_size=10,
        retry_delay_seconds=0,
        max_attempts=3,
    )
    assert await dispatcher.dispatch_once() == 2

    outbox_events = await get_outbox_events(integration_sessionmaker)
    assert [(event.topic, event.status, event.attempts) for event in outbox_events] == [
        (VEHICLE_EVENTS_TOPIC, "pending", 1),
        (AUDIT_EVENTS_TOPIC, "pending", 1),
    ]
    assert all(event.last_error == "kafka is down" for event in outbox_events)


async def test_vehicle_visibility_filters_list_and_blocks_hidden_vehicle(
    integration_client,
    integration_sessionmaker,
):
    visible_enterprise, model = await seed_enterprise_and_model(integration_sessionmaker)
    async with integration_sessionmaker() as session:
        hidden_enterprise = Enterprise(
            name="Hidden enterprise",
            settlement="Kazan",
            timezone="Europe/Moscow",
        )
        session.add(hidden_enterprise)
        await session.commit()
        await session.refresh(hidden_enterprise)

    visible_vehicle = await seed_vehicle(
        integration_sessionmaker,
        enterprise=visible_enterprise,
        model=model,
        number="А111АА77",
    )
    hidden_vehicle = await seed_vehicle(
        integration_sessionmaker,
        enterprise=hidden_enterprise,
        model=model,
        number="А222АА77",
    )

    async def _visible_enterprise_ids():
        return {visible_enterprise.id}

    fastapi_app.dependency_overrides[get_visible_enterprise_ids] = _visible_enterprise_ids

    list_response = await integration_client.get("/api/vehicles")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [visible_vehicle.id]

    hidden_response = await integration_client.get(f"/api/vehicles/{hidden_vehicle.id}")
    assert hidden_response.status_code == 403


async def test_vehicle_track_endpoint_reads_postgis_points_in_requested_range(
    integration_client,
    integration_sessionmaker,
):
    enterprise, model = await seed_enterprise_and_model(integration_sessionmaker)
    vehicle = await seed_vehicle(
        integration_sessionmaker,
        enterprise=enterprise,
        model=model,
        number="А333АА77",
    )
    started_at = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    await seed_track_points(
        integration_sessionmaker,
        vehicle_id=vehicle.id,
        started_at=started_at,
    )

    response = await integration_client.get(
        f"/api/vehicles/{vehicle.id}/track",
        params={
            "date_from": "2026-06-01T09:55:00+00:00",
            "date_to": "2026-06-01T10:10:00+00:00",
        },
    )

    assert response.status_code == 200
    points = response.json()
    assert len(points) == 2
    assert points[0]["latitude"] == pytest.approx(55.751244)
    assert points[0]["longitude"] == pytest.approx(37.618423)
    assert points[1]["latitude"] == pytest.approx(55.752)
    assert points[1]["longitude"] == pytest.approx(37.62)
    assert points[0]["recorded_at_enterprise"].endswith("+03:00")

    geojson_response = await integration_client.get(
        f"/api/vehicles/{vehicle.id}/track",
        params={
            "date_from": "2026-06-01T09:55:00+00:00",
            "date_to": "2026-06-01T10:10:00+00:00",
            "format": "geojson",
        },
    )

    assert geojson_response.status_code == 200
    geojson = geojson_response.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2
    assert geojson["features"][0]["geometry"] == {
        "type": "Point",
        "coordinates": [37.618423, 55.751244],
    }
    assert geojson["features"][0]["properties"]["enterprise_timezone"] == "Europe/Moscow"
