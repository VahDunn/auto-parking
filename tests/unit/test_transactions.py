from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from auto_parking.core.domain.models import VehicleModel
from auto_parking.deps import commons
from auto_parking.repo.vehicle import VehicleRepository


class FakeSessionContext:
    def __init__(self):
        self.session = AsyncMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.asyncio
async def test_get_db_yields_session_without_finishing_transaction(monkeypatch):
    context = FakeSessionContext()
    monkeypatch.setattr(commons, "AsyncSessionLocal", lambda: context)

    generator = commons.get_db()
    session = await anext(generator)

    assert session is context.session

    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    context.session.commit.assert_not_awaited()
    context.session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_db_does_not_rollback_exception(monkeypatch):
    context = FakeSessionContext()
    monkeypatch.setattr(commons, "AsyncSessionLocal", lambda: context)

    generator = commons.get_db()
    session = await anext(generator)

    assert session is context.session

    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))

    context.session.commit.assert_not_awaited()
    context.session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_repository_commits_successful_write():
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    repo = VehicleRepository(db)
    repo.get_by_id = AsyncMock(return_value=vehicle_orm())

    await repo.create(vehicle_data())

    db.commit.assert_awaited_once_with()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_repository_rolls_back_failed_write():
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock(side_effect=RuntimeError("boom"))
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    repo = VehicleRepository(db)

    with pytest.raises(RuntimeError, match="boom"):
        await repo.create(vehicle_data())

    db.commit.assert_awaited_once_with()
    db.rollback.assert_awaited_once_with()


def vehicle_data() -> dict:
    model = VehicleModel(
        id=None,
        price=1000,
        mileage=500,
        vehicle_number="A123BC77",
        owners_count=1,
        accident_number=0,
        manufacture_year=2020,
        model_id=2,
        enterprise_id=10,
        color="black",
        purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    return {
        "price": model.price,
        "mileage": model.mileage,
        "vehicle_number": model.vehicle_number,
        "owners_count": model.owners_count,
        "accident_number": model.accident_number,
        "manufacture_year": model.manufacture_year,
        "model_id": model.model_id,
        "enterprise_id": model.enterprise_id,
        "color": model.color,
        "active_driver_id": model.active_driver_id,
        "purchased_at_utc": model.purchased_at_utc,
    }


def vehicle_orm():
    return SimpleNamespace(
        id=1,
        price=1000,
        mileage=500,
        vehicle_number="A123BC77",
        owners_count=1,
        accident_number=0,
        manufacture_year=2020,
        model_id=2,
        color="black",
        enterprise_id=10,
        drivers=[],
        active_driver_id=None,
        purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
