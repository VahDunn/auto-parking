from fastapi import APIRouter

from auto_parking.api.schemas.vehicle import VehicleFilter, VehicleOut
from auto_parking.deps.filters import dep_vehicle_filter
from auto_parking.deps.services import dep_vehicle_service
from auto_parking.service.vehicle import VehicleService

router = APIRouter()


@router.get(
    "",
    response_model=list[VehicleOut],
)
async def get_vehicles(
    filter: VehicleFilter = dep_vehicle_filter,
    service: VehicleService = dep_vehicle_service,
):
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
