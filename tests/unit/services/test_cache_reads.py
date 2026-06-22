from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.core.domain.enums import TrackFormat
from auto_parking.service.vehicle import VehicleService
from auto_parking.service.vehicle_model import VehicleModelService
from auto_parking.service.vehicle_track import VehicleTrackService

pytestmark = pytest.mark.asyncio


class FakeCacheClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, int]] = []
        self.delete_calls: list[str] = []

    async def get_text(self, key: str) -> str | None:
        return self.values.get(key)

    async def set_text(self, key: str, value: str, *, ttl_seconds: int) -> None:
        self.values[key] = value
        self.set_calls.append((key, ttl_seconds))

    async def delete_text(self, key: str) -> None:
        self.values.pop(key, None)
        self.delete_calls.append(key)

    async def delete_prefix(self, prefix: str) -> None:
        for key in list(self.values):
            if key.startswith(prefix):
                self.values.pop(key)


def vehicle_orm():
    return SimpleNamespace(
        id=1,
        price=1000,
        mileage=500,
        vehicle_number="А123ВС77",
        owners_count=1,
        accident_number=0,
        manufacture_year=2020,
        model_id=2,
        color="black",
        enterprise_id=10,
        drivers=[SimpleNamespace(id=11)],
        active_driver_id=11,
        purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        enterprise=SimpleNamespace(timezone="Europe/Moscow"),
    )


async def test_vehicle_service_get_by_id_uses_cached_domain_model():
    repo = AsyncMock()
    repo.get_by_id.return_value = vehicle_orm()
    cache = FakeCacheClient()
    service = VehicleService(repo, cache=cache, cache_ttl_seconds=123)

    first = await service.get_by_id(1)
    second = await service.get_by_id(1)

    assert first == second
    repo.get_by_id.assert_awaited_once_with(1)
    assert cache.set_calls == [("vehicle:id:1", 123)]


async def test_vehicle_service_delete_invalidates_cached_vehicle():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    repo.delete.return_value = True
    cache = FakeCacheClient()
    cache.values["vehicle:id:1"] = "{}"
    service = VehicleService(repo, cache=cache)

    assert await service.delete(1) is True

    assert cache.delete_calls == ["vehicle:id:1"]


async def test_vehicle_model_service_get_by_name_uses_normalized_cache_key():
    repo = AsyncMock()
    repo.get_by_name.return_value = SimpleNamespace(
        id=2,
        name="Sedan",
        type="car",
        horse_powers=150,
        seats_number=5,
        fuel_capacity_liters=60,
    )
    cache = FakeCacheClient()
    service = VehicleModelService(repo, cache=cache, cache_ttl_seconds=3600)

    first = await service.get_by_name(" Sedan ")
    second = await service.get_by_name("sedan")

    assert first == second
    repo.get_by_name.assert_awaited_once_with("Sedan")
    assert cache.set_calls == [("vehicle-model:name:sedan", 3600)]


async def test_vehicle_track_service_reuses_cached_domain_track():
    track_repo = AsyncMock()
    track_repo.get.return_value = [
        SimpleNamespace(
            id=10,
            recorded_at_utc=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
            latitude=55.75,
            longitude=37.62,
        )
    ]
    cache = FakeCacheClient()
    service = VehicleTrackService(
        track_repo,
        cache=cache,
        cache_ttl_seconds=300,
    )
    date_from = datetime(2026, 5, 1, tzinfo=UTC)
    date_to = datetime(2026, 5, 2, tzinfo=UTC)

    first_track = await service.get_track(
        1,
        date_from,
        date_to,
        TrackFormat.json,
        "Europe/Moscow",
    )
    second_track = await service.get_track(
        1,
        date_from,
        date_to,
        TrackFormat.json,
        "Europe/Moscow",
    )

    assert first_track == second_track
    assert first_track[0].recorded_at_utc == datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    assert first_track[0].recorded_at_enterprise.isoformat() == "2026-05-01T13:00:00+03:00"
    assert first_track[0].latitude == 55.75
    track_repo.get.assert_awaited_once()
    assert cache.set_calls == [
        (
            "vehicle-track-domain:1:json:Europe/Moscow:"
            "2026-05-01T00:00:00+00:00:2026-05-02T00:00:00+00:00",
            300,
        )
    ]
