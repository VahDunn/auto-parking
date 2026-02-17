from fastapi import APIRouter, Depends, HTTPException

from auto_parking.api.schemas.vehicle import VehicleFilter, VehicleOut
from auto_parking.core.security.auth import get_actor
from auto_parking.db.models import Manager
from auto_parking.deps.commons import dep_query
from auto_parking.deps.services import dep_manager_service, dep_vehicle_service
from auto_parking.service.vehicle import VehicleService

router = APIRouter()
actor_dep = Depends(get_actor)


@router.get("", response_model=list[VehicleOut])
async def get_vehicles(
    id: list[int] | None = dep_query,
    enterprise_ids: list[int] | None = dep_query,
    driver_id: int | None = dep_query,
    actor=actor_dep,
    manager_service=dep_manager_service,
    service: VehicleService = dep_vehicle_service,
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

    filter_obj = VehicleFilter(id=id, enterprise_ids=enterprise_ids, driver_id=driver_id)
    return await service.get(filter_obj)


@router.get("/{id}", response_model=VehicleOut)
async def get_vehicle(
    id: int,
    actor=actor_dep,
    manager_service=dep_manager_service,
    service: VehicleService = dep_vehicle_service,
):
    vehicle = await service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if actor["type"] == "manager":
        manager: Manager = await manager_service.get_by_id(actor["id"])
        visible = {e.id for e in manager.enterprises}
        if vehicle.enterprise_id not in visible:
            raise HTTPException(status_code=404)

    return vehicle
