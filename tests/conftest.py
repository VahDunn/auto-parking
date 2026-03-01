from unittest.mock import AsyncMock

import httpx
import pytest_asyncio
from asgi_lifespan import LifespanManager

from auto_parking.core.domain.user_role import UserRole
from auto_parking.deps.commons import dep_actor
from auto_parking.deps.services import dep_enterprise_service, dep_vehicle_service
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.main import app as fastapi_app


class FakeActor:
    def __init__(self, role: UserRole, id: int = 1):
        self.role = role
        self.id = id


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=fastapi_app)

    async with LifespanManager(fastapi_app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as ac:
            yield ac


@pytest_asyncio.fixture
def vehicle_service_mock():
    svc = AsyncMock()
    # методы сервиса (должны быть awaitable)
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.create = AsyncMock()
    svc.update = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest_asyncio.fixture
def enterprise_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest_asyncio.fixture
def overrides():
    yield fastapi_app.dependency_overrides
    fastapi_app.dependency_overrides.clear()


def set_actor_override(overrides, role: UserRole, actor_id: int = 1):
    async def _dep():
        return FakeActor(role=role, id=actor_id)

    overrides[dep_actor] = _dep


def set_visible_ids_override(overrides, ids: set[int] | None):
    async def _dep():
        return ids

    overrides[get_visible_enterprise_ids] = _dep


def set_vehicle_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_vehicle_service] = _dep


def set_enterprise_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_enterprise_service] = _dep
