from fastapi import APIRouter, Depends, HTTPException, Query, status

from auto_parking.app.deps.access import require_manager_or_higher
from auto_parking.app.deps.services import dep_driver_service
from auto_parking.app.deps.visibility import (
    apply_enterprise_visibility,
    ensure_enterprise_visible,
    get_visible_enterprise_ids,
)
from auto_parking.app.filter import DriverFilter
from auto_parking.app.schemas.driver import DriverOut
from auto_parking.app.service.driver import DriverService
from auto_parking.core.domain.models import DriverModel

router = APIRouter()

dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


def _driver_out(driver: DriverModel) -> DriverOut:
    data = driver.to_dict()
    if data["active_vehicle_id"] is None:
        data["active_vehicle_id"] = -1
    return DriverOut(**data)


def _parse_int_list(value: str | None) -> list[int] | None:
    if value is None or value.strip() == "":
        return None

    return [int(item.strip()) for item in value.split(",") if item.strip()]


@router.get("", response_model=list[DriverOut], dependencies=[dep_actor_guard])
async def get_drivers(
    id: str | None = Query(None),
    enterprise_ids: str | None = Query(None),
    vehicle_id: int | None = Query(None),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: DriverService = dep_driver_service,
):
    parsed_ids = _parse_int_list(id)
    parsed_enterprise_ids = _parse_int_list(enterprise_ids)

    parsed_enterprise_ids = apply_enterprise_visibility(
        parsed_enterprise_ids,
        visible_enterprise_ids,
    )
    if visible_enterprise_ids is not None and parsed_enterprise_ids == []:
        return []

    filter_obj = DriverFilter(
        id=parsed_ids,
        enterprise_ids=parsed_enterprise_ids,
        vehicle_id=vehicle_id,
    )
    return [_driver_out(driver) for driver in await service.get(filter_obj)]


@router.get("/{id}", response_model=DriverOut, dependencies=[dep_actor_guard])
async def get_driver(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: DriverService = dep_driver_service,
):
    driver = await service.get_by_id(id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    ensure_enterprise_visible(driver.enterprise_id, visible_enterprise_ids)
    return _driver_out(driver)
