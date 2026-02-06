from fastapi import APIRouter

from auto_parking.api.schemas.driver import DriverFilter, DriverOut
from auto_parking.deps.commons import dep_query
from auto_parking.deps.services import dep_driver_service
from auto_parking.service.driver import DriverService

router = APIRouter()


@router.get("", response_model=list[DriverOut])
async def get_drivers(
    id: list[int] | None = dep_query,
    enterprise_id: int | None = dep_query,
    vehicle_id: int | None = dep_query,
    service: DriverService = dep_driver_service,
):
    filter = DriverFilter(
        id=id,
        enterprise_id=enterprise_id,
        vehicle_id=vehicle_id,
    )
    return await service.get(filter)


@router.get("/{id}", response_model=DriverOut)
async def get_driver(
    id: int,
    service: DriverService = dep_driver_service,
):
    return await service.get_by_id(id)
