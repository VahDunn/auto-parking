import os
from unittest.mock import AsyncMock, Mock

os.environ.setdefault(
    "AUDIT_DATABASE_URL",
    "postgresql+asyncpg://auto_parking:change-me@localhost:5432/auto_parking_test",
)

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager

from auto_parking.app.deps.access import require_manager_or_higher
from auto_parking.app.deps.services import (
    dep_driver_service,
    dep_enterprise_service,
    dep_export_service,
    dep_gpx_import_service,
    dep_import_service,
    dep_notification_service,
    dep_report_service,
    dep_reports_pdf_service,
    dep_trip_service,
    dep_trip_track_service,
    dep_user_service,
    dep_vehicle_model_service,
    dep_vehicle_service,
    dep_vehicle_track_service,
)
from auto_parking.app.deps.visibility import get_visible_enterprise_ids
from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.main import app as fastapi_app


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_INTEGRATION") == "1":
        return

    skip_integration = pytest.mark.skip(reason="set RUN_INTEGRATION=1 to run integration tests")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


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


@pytest.fixture
def driver_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    return svc


@pytest.fixture
def user_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    return svc


@pytest.fixture
def vehicle_model_service_mock():
    svc = AsyncMock()
    svc.get_all = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.get_by_name = AsyncMock()
    return svc


@pytest.fixture
def export_service_mock():
    svc = AsyncMock()
    svc.export_enterprise_full = AsyncMock()
    svc.export_enterprise_guid_dump = AsyncMock()
    svc.export_enterprise_vehicles = AsyncMock()
    svc.export_vehicle_trips = AsyncMock()
    return svc


@pytest.fixture
def import_service_mock():
    svc = AsyncMock()
    svc.import_enterprise_json = AsyncMock()
    svc.import_enterprise_csv = AsyncMock()
    return svc


@pytest.fixture
def report_service_mock():
    svc = AsyncMock()
    svc.get_available_reports = AsyncMock()
    svc.get_all = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.create = AsyncMock()
    svc.rebuild = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest.fixture
def notification_service_mock():
    svc = AsyncMock()
    svc.get_for_user = AsyncMock()
    svc.mark_read = AsyncMock()
    svc.mark_all_read = AsyncMock()
    svc.unread_count = AsyncMock()
    return svc


@pytest.fixture
def reports_pdf_service_mock():
    svc = Mock()
    svc.build.return_value = b"%PDF-1.4 test"
    return svc


@pytest.fixture
def gpx_import_service_mock():
    svc = AsyncMock()
    svc.import_vehicle_trip = AsyncMock()
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


def set_driver_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_driver_service)] = _dep


def set_user_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_user_service)] = _dep


def set_vehicle_model_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_vehicle_model_service)] = _dep


def set_export_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_export_service)] = _dep


def set_import_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_import_service)] = _dep


def set_report_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_report_service)] = _dep


def set_notification_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_notification_service)] = _dep


def set_reports_pdf_service_override(overrides, mock):
    def _dep():
        return mock

    overrides[dep_callable(dep_reports_pdf_service)] = _dep


def set_gpx_import_service_override(overrides, mock):
    async def _dep():
        return mock

    overrides[dep_callable(dep_gpx_import_service)] = _dep
