from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager

from auto_parking.core.enums.user_role import UserRole
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import (
    dep_enterprise_service,
    dep_trip_service,
    dep_trip_track_service,
    dep_vehicle_service,
    dep_vehicle_track_service,
)
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.main import app as fastapi_app


class FakeActor:
    def __init__(self, role: UserRole, id: int = 1):
        self.role = role
        self.id = id


def dep_callable(dep_obj):
    return getattr(dep_obj, "dependency", dep_obj)


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=fastapi_app)

    async with LifespanManager(fastapi_app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as ac:
            yield ac


@pytest.fixture
def overrides():
    yield fastapi_app.dependency_overrides
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def vehicle_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.create = AsyncMock()
    svc.update = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest.fixture
def vehicle_track_service_mock():
    svc = AsyncMock()
    svc.get_track = AsyncMock()
    return svc


@pytest.fixture
def trip_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.get_vehicle_trips_in_range = AsyncMock()
    svc.create = AsyncMock()
    svc.update = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest.fixture
def trip_track_service_mock():
    svc = AsyncMock()
    svc.get_track = AsyncMock()
    svc.get_grouped_track = AsyncMock()
    return svc


@pytest.fixture
def enterprise_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.delete = AsyncMock()
    return svc


def set_actor_override(overrides, role: UserRole, actor_id: int = 1):
    async def _dep():
        return FakeActor(role=role, id=actor_id)

    overrides[require_manager_or_higher] = _dep


def set_visible_ids_override(overrides, ids: set[int] | None):
    async def _dep():
        return ids

    overrides[get_visible_enterprise_ids] = _dep


def set_vehicle_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_vehicle_service)] = _dep


def set_vehicle_track_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_vehicle_track_service)] = _dep


def set_trip_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_trip_service)] = _dep


def set_trip_track_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_trip_track_service)] = _dep


def set_enterprise_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_enterprise_service)] = _dep
