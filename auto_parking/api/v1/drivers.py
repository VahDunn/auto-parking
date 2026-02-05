from fastapi import APIRouter

from auto_parking.api.schemas.driver import DriverOut
from auto_parking.deps.services import depends_driver_service
from auto_parking.service.driver import DriverService

router = APIRouter()


@router.get("", response_model=list[DriverOut])
async def get_drivers(service: DriverService = depends_driver_service):
    return await service.get()


@router.get("/{id}", response_model=DriverOut)
async def get_driver(id: int, service: DriverService = depends_driver_service):
    return await service.get_by_id(id)
