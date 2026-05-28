from fastapi import APIRouter, HTTPException, Query

from auto_parking.api.schemas.driver import DriverOut
from auto_parking.core.domain.models import DriverModel
from auto_parking.deps.commons import dep_actor
from auto_parking.deps.services import dep_driver_service, dep_user_service
from auto_parking.filter import DriverFilter
from auto_parking.service.driver import DriverService

router = APIRouter()


def _driver_out(driver: DriverModel) -> DriverOut:
    data = driver.to_dict()
    if data["active_vehicle_id"] is None:
        data["active_vehicle_id"] = -1
    return DriverOut(**data)


def _parse_int_list(value: str | None) -> list[int] | None:
    if value is None or value.strip() == "":
        return None

    return [int(item.strip()) for item in value.split(",") if item.strip()]


@router.get("", response_model=list[DriverOut])
async def get_drivers(
    id: str | None = Query(None),
    enterprise_ids: str | None = Query(None),
    vehicle_id: int | None = Query(None),
    actor=dep_actor,
    manager_service=dep_user_service,
    service: DriverService = dep_driver_service,
):
    parsed_ids = _parse_int_list(id)
    parsed_enterprise_ids = _parse_int_list(enterprise_ids)

    if actor.role == "manager":
        manager = await manager_service.get_by_id(actor.id)
        visible = {e.id for e in manager.enterprises}

        if parsed_enterprise_ids is not None:
            allowed = list(set(parsed_enterprise_ids) & visible)
            if not allowed:
                return []
            parsed_enterprise_ids = allowed
        else:
            parsed_enterprise_ids = list(visible)

    filter_obj = DriverFilter(
        id=parsed_ids,
        enterprise_ids=parsed_enterprise_ids,
        vehicle_id=vehicle_id,
    )
    return [_driver_out(driver) for driver in await service.get(filter_obj)]


@router.get("/{id}", response_model=DriverOut)
async def get_driver(
    id: int,
    actor=dep_actor,
    manager_service=dep_user_service,
    service: DriverService = dep_driver_service,
):
    driver = await service.get_by_id(id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    if actor.role == "manager":
        manager = await manager_service.get_by_id(actor.id)
        visible = {e.id for e in manager.enterprises}
        if driver.enterprise_id not in visible:
            raise HTTPException(status_code=404)

    return _driver_out(driver)
