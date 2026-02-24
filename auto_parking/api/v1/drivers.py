from fastapi import APIRouter, HTTPException

from auto_parking.api.schemas.driver import DriverFilter, DriverOut
from auto_parking.core.security.auth import actor_dep
from auto_parking.db.models import Manager
from auto_parking.deps.commons import dep_query
from auto_parking.deps.services import dep_driver_service, dep_manager_service
from auto_parking.service.driver import DriverService

router = APIRouter()


@router.get("", response_model=list[DriverOut])
async def get_drivers(
    id: list[int] | None = dep_query,
    enterprise_ids: list[int] | None = dep_query,
    vehicle_id: int | None = dep_query,
    actor=actor_dep,
    manager_service=dep_manager_service,
    service: DriverService = dep_driver_service,
):
    if actor["type"] == "manager":
        manager: Manager = await manager_service.get_by_id(actor["id"])
        visible = {e.id for e in manager.enterprises}

        if enterprise_ids is not None:
            allowed = list(set(enterprise_ids) & visible)
            if not allowed:
                return []
            enterprise_ids = allowed
        else:
            enterprise_ids = list(visible)

    filter_obj = DriverFilter(
        id=id,
        enterprise_ids=enterprise_ids,
        vehicle_id=vehicle_id,
    )
    return await service.get(filter_obj)


@router.get("/{id}", response_model=DriverOut)
async def get_driver(
    id: int,
    actor=actor_dep,
    manager_service=dep_manager_service,
    service: DriverService = dep_driver_service,
):
    driver = await service.get_by_id(id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    if actor["type"] == "manager":
        manager: Manager = await manager_service.get_by_id(actor["id"])
        visible = {e.id for e in manager.enterprises}
        if driver.enterprise_id not in visible:
            raise HTTPException(status_code=404)

    return driver
