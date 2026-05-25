from types import SimpleNamespace

import pytest

from auto_parking.core.domain.models import DriverModel
from auto_parking.core.security.actor import get_current_actor
from tests.conftest import set_driver_service_override, set_user_service_override

pytestmark = pytest.mark.asyncio


async def test_drivers_list_and_detail_apply_manager_visibility(
    client,
    overrides,
    driver_service_mock,
    user_service_mock,
):
    set_user_service_override(overrides, user_service_mock)
    set_driver_service_override(overrides, driver_service_mock)

    async def _actor():
        return SimpleNamespace(id=5, role="manager")

    overrides[get_current_actor] = _actor
    user_service_mock.get_by_id.return_value = SimpleNamespace(enterprises=[SimpleNamespace(id=10)])
    driver = DriverModel(
        id=11,
        name="Driver",
        salary_rub=100000,
        enterprise_id=10,
        vehicles=[1],
        active_vehicle_id=1,
    )
    driver_service_mock.get.return_value = [driver]
    driver_service_mock.get_by_id.return_value = driver

    list_response = await client.get("/api/drivers", params={"enterprise_ids": "10,20"})
    detail_response = await client.get("/api/drivers/11")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == 11
    assert detail_response.status_code == 200
    assert detail_response.json()["enterprise_id"] == 10
