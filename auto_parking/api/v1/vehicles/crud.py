from fastapi import APIRouter, HTTPException, Query, status

from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate
from auto_parking.api.v1.vehicles.common import (
    apply_enterprise_visibility,
    dep_actor_guard,
    dep_visible_ids,
    ensure_vehicle_visible,
    parse_int_list,
    vehicle_out,
)
from auto_parking.core.domain.models import VehicleCreateModel, VehicleUpdateModel
from auto_parking.deps.services import dep_vehicle_service
from auto_parking.filter import VehicleFilter
from auto_parking.service.vehicle import VehicleService

router = APIRouter()


@router.get(
    "",
    response_model=list[VehicleOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicles(
    id: str | None = Query(None),
    vehicle_number_prefix: str | None = Query(None),
    enterprise_ids: str | None = Query(None),
    driver_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    parsed_ids = parse_int_list(id)
    parsed_enterprise_ids = parse_int_list(enterprise_ids)

    parsed_enterprise_ids = apply_enterprise_visibility(
        parsed_enterprise_ids,
        visible_enterprise_ids,
    )

    if visible_enterprise_ids is not None and parsed_enterprise_ids == []:
        return []

    return [
        vehicle_out(vehicle)
        for vehicle in await service.get(
            VehicleFilter(
                id=parsed_ids,
                vehicle_number_prefix=vehicle_number_prefix,
                enterprise_ids=parsed_enterprise_ids,
                driver_id=driver_id,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
            )
        )
    ]


@router.get(
    "/{id}",
    response_model=VehicleOut,
    dependencies=[dep_actor_guard],
)
async def get_vehicle(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    vehicle = await service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    ensure_vehicle_visible(vehicle, visible_enterprise_ids)
    return vehicle_out(vehicle)


@router.post(
    "",
    response_model=VehicleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[dep_actor_guard],
)
async def create_vehicle(
    payload: VehicleCreate,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    if visible_enterprise_ids is not None and payload.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return vehicle_out(await service.create(VehicleCreateModel(**payload.model_dump())))


@router.patch(
    "/{id}",
    response_model=VehicleOut,
    dependencies=[dep_actor_guard],
)
async def update_vehicle(
    id: int,
    payload: VehicleUpdate,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    current = await service.get_by_id(id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    ensure_vehicle_visible(current, visible_enterprise_ids)

    updated = await service.update(
        id,
        VehicleUpdateModel(changes=payload.model_dump(exclude_unset=True)),
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    return vehicle_out(updated)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[dep_actor_guard],
)
async def delete_vehicle(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    current = await service.get_by_id(id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    ensure_vehicle_visible(current, visible_enterprise_ids)

    ok = await service.delete(id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
