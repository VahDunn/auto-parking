from fastapi import APIRouter, Query

from auto_parking.api.schemas.vehicle import VehicleFilter, VehicleOut
from auto_parking.deps.services import dep_vehicle_service
from auto_parking.service.vehicle import VehicleService

router = APIRouter()


@router.get(
    "",
    response_model=list[VehicleOut],
)
async def get_vehicles(
    id: list[int] | None = Query(default=None),
    enterprise_id: int | None = Query(default=None),
    driver_id: int | None = Query(default=None),
    service: VehicleService = dep_vehicle_service,
):
    filter = VehicleFilter(id=id, enterprise_id=enterprise_id, driver_id=driver_id)
    return await service.get(filter)


@router.get(
    "/{id}",
    response_model=VehicleOut,
)
async def get_vehicle(
    id: int,
    service: VehicleService = dep_vehicle_service,
):
    return await service.get_by_id(id)
