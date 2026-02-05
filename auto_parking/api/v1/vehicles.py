from fastapi import APIRouter

from auto_parking.api.schemas.vehicle import VehicleOut
from auto_parking.deps.services import depends_vehicle_service
from auto_parking.service.vehicle import VehicleService

router = APIRouter()


@router.get(
    "",
    response_model=list[VehicleOut],
)
async def get_vehicles(
    service: VehicleService = depends_vehicle_service,
):
    return await service.get()


@router.get(
    "/{id}",
    response_model=VehicleOut,
)
async def get_vehicle(
    id: int,
    service: VehicleService = depends_vehicle_service,
):
    return await service.get_by_id(id)
