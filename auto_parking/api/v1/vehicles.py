from fastapi import APIRouter

from auto_parking.api.schemas.vehicle import VehicleFilter, VehicleOut
from auto_parking.deps.commons import dep_query
from auto_parking.deps.services import dep_vehicle_service
from auto_parking.service.vehicle import VehicleService

router = APIRouter()


@router.get(
    "",
    response_model=list[VehicleOut],
)
async def get_vehicles(
    id: list[int] | None = dep_query,
    enterprise_id: int | None = dep_query,
    driver_id: int | None = dep_query,
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
