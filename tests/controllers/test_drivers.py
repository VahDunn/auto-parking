import pytest

from auto_parking.core.domain.enums import UserRole
from auto_parking.core.domain.models import DriverModel
from auto_parking.filter import DriverFilter
from tests.conftest import (
    set_actor_override,
    set_driver_service_override,
    set_visible_ids_override,
)

pytestmark = pytest.mark.asyncio


async def test_drivers_list_and_detail_apply_manager_visibility(
    client,
    overrides,
    driver_service_mock,
):
    set_actor_override(overrides, UserRole.manager, actor_id=5)
    set_visible_ids_override(overrides, {10})
    set_driver_service_override(overrides, driver_service_mock)
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
    filter_obj = driver_service_mock.get.await_args.args[0]
    assert isinstance(filter_obj, DriverFilter)
    assert filter_obj.enterprise_ids == [10]
    assert detail_response.status_code == 200
    assert detail_response.json()["enterprise_id"] == 10


async def test_driver_detail_forbidden_when_enterprise_not_visible(
    client,
    overrides,
    driver_service_mock,
):
    set_actor_override(overrides, UserRole.manager, actor_id=5)
    set_visible_ids_override(overrides, {10})
    set_driver_service_override(overrides, driver_service_mock)
    driver_service_mock.get_by_id.return_value = DriverModel(
        id=11,
        name="Driver",
        salary_rub=100000,
        enterprise_id=20,
        vehicles=[1],
        active_vehicle_id=1,
    )

    response = await client.get("/api/drivers/11")

    assert response.status_code == 403
