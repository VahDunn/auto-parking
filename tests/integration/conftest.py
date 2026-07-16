import os
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auto_parking.app.deps.access import require_manager_or_higher
from auto_parking.app.deps.commons import get_db
from auto_parking.app.deps.visibility import get_visible_enterprise_ids
from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.infrastructure.cache.null import NullCacheClient
from auto_parking.infrastructure.db.models import Base
from auto_parking.main import app as fastapi_app
from tests.conftest import FakeActor


class CapturingEventProducer:
    def __init__(self):
        self.published = []

    async def publish(self, topic, event, *, key=None):
        self.published.append((topic, event, key))

    async def close(self):
        return None


@pytest_asyncio.fixture
async def integration_sessionmaker() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for integration tests")

    engine = create_async_engine(database_url, future=True)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    yield sessionmaker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def captured_event_producer(monkeypatch):
    producer = CapturingEventProducer()
    monkeypatch.setattr(
        "auto_parking.app.deps.services.get_cache_client",
        lambda: NullCacheClient(),
    )
    return producer


@pytest_asyncio.fixture
async def integration_client(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
    captured_event_producer: CapturingEventProducer,
):
    async def _get_db():
        async with integration_sessionmaker() as session:
            yield session

    async def _require_manager_or_higher():
        return FakeActor(role=UserRole.admin, id=1)

    async def _visible_enterprise_ids():
        return None

    fastapi_app.dependency_overrides[get_db] = _get_db
    fastapi_app.dependency_overrides[require_manager_or_higher] = _require_manager_or_higher
    fastapi_app.dependency_overrides[get_visible_enterprise_ids] = _visible_enterprise_ids

    transport = httpx.ASGITransport(app=fastapi_app)
    async with LifespanManager(fastapi_app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client

    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_integration_client(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
    captured_event_producer: CapturingEventProducer,
):
    async def _get_db():
        async with integration_sessionmaker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _get_db

    transport = httpx.ASGITransport(app=fastapi_app)
    async with LifespanManager(fastapi_app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client

    fastapi_app.dependency_overrides.clear()
