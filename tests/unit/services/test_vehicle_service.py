from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.app.filter import VehicleFilter
from auto_parking.app.service.vehicle import VehicleService
from auto_parking.core.domain.models import VehicleModel
from event_bus.contracts import AUDIT_EVENTS_TOPIC, VEHICLE_EVENTS_TOPIC

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
    assert result[0].enterprise_id == 10
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
            vehicle_number=" а123вс77 ",
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
    assert data["vehicle_number"] == "А123ВС77"
    assert data["purchased_at_utc"] == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


async def test_vehicle_service_create_publishes_vehicle_event():
    repo = AsyncMock()
    repo.create.return_value = vehicle_orm()
    repo.manager_ids_for_enterprise.return_value = [21, 22]
    producer = AsyncMock()
    service = VehicleService(repo, event_producer=producer)

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
        )
    )

    assert producer.publish.await_count == 2
    topic, event = producer.publish.await_args_list[0].args
    assert topic == VEHICLE_EVENTS_TOPIC
    assert event.event_type == "vehicle.created"
    assert event.payload["vehicle_id"] == 1
    assert event.payload["vehicle_number"] == "А123ВС77"
    assert event.payload["enterprise_id"] == 10
    assert event.payload["manager_user_ids"] == [21, 22]
    assert producer.publish.await_args_list[0].kwargs == {"key": "1"}
    audit_topic, audit_event = producer.publish.await_args_list[1].args
    assert audit_topic == AUDIT_EVENTS_TOPIC
    assert audit_event == event
    assert producer.publish.await_args_list[1].kwargs == {"key": "1"}


async def test_vehicle_service_create_stores_vehicle_event_in_outbox_when_configured():
    repo = AsyncMock()
    repo.db.commit = AsyncMock()
    repo.db.rollback = AsyncMock()
    repo.create_uncommitted.return_value = vehicle_orm()
    repo.manager_ids_for_enterprise.return_value = [21, 22]
    outbox_repo = AsyncMock()
    producer = AsyncMock()
    service = VehicleService(repo, event_producer=producer, outbox_repo=outbox_repo)

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
        )
    )

    repo.create.assert_not_awaited()
    repo.create_uncommitted.assert_awaited_once()
    repo.db.commit.assert_awaited_once()
    repo.db.rollback.assert_not_awaited()
    producer.publish.assert_not_awaited()
    assert outbox_repo.add_event.await_count == 2

    first_event = outbox_repo.add_event.await_args_list[0].kwargs["event"]
    assert outbox_repo.add_event.await_args_list[0].kwargs["topic"] == VEHICLE_EVENTS_TOPIC
    assert outbox_repo.add_event.await_args_list[0].kwargs["key"] == "1"
    assert first_event.event_type == "vehicle.created"
    assert first_event.payload["manager_user_ids"] == [21, 22]
    assert outbox_repo.add_event.await_args_list[1].kwargs["topic"] == AUDIT_EVENTS_TOPIC


async def test_vehicle_service_rolls_back_when_outbox_write_fails():
    repo = AsyncMock()
    repo.db.commit = AsyncMock()
    repo.db.rollback = AsyncMock()
    repo.create_uncommitted.return_value = vehicle_orm()
    repo.manager_ids_for_enterprise.return_value = [21, 22]
    outbox_repo = AsyncMock()
    outbox_repo.add_event.side_effect = RuntimeError("outbox failed")
    service = VehicleService(repo, outbox_repo=outbox_repo)

    with pytest.raises(RuntimeError, match="outbox failed"):
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
            )
        )

    repo.db.commit.assert_not_awaited()
    repo.db.rollback.assert_awaited_once()


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
