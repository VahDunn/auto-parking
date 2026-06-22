from time import perf_counter

from fastapi import APIRouter, HTTPException, Query, status

from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate
from auto_parking.api.v1.vehicles.common import (
    dep_actor_guard,
    dep_visible_ids,
    ensure_vehicle_visible,
    enterprise_timezones,
    parse_int_list,
    vehicle_out,
)
from auto_parking.deps.services import dep_enterprise_service, dep_vehicle_service
from auto_parking.deps.visibility import apply_enterprise_visibility
from auto_parking.filter import EnterpriseFilter, VehicleFilter
from auto_parking.observability.performance import log_operation_stage
from auto_parking.service.enterprise import EnterpriseService
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

    operation_started_at = perf_counter()
    stage_started_at = perf_counter()
    vehicles = await service.get(
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
    log_operation_stage(
        operation="vehicles_list",
        stage="vehicle_service_get",
        duration_seconds=perf_counter() - stage_started_at,
        vehicle_count=len(vehicles),
    )

    stage_started_at = perf_counter()
    response = [vehicle_out(vehicle, vehicle.enterprise_timezone) for vehicle in vehicles]
    log_operation_stage(
        operation="vehicles_list",
        stage="api_mapping",
        duration_seconds=perf_counter() - stage_started_at,
        vehicle_count=len(response),
    )
    log_operation_stage(
        operation="vehicles_list",
        stage="handler_total_without_fastapi_serialization",
        duration_seconds=perf_counter() - operation_started_at,
        vehicle_count=len(response),
    )
    return response


@router.get(
    "/{id}",
    response_model=VehicleOut,
    dependencies=[dep_actor_guard],
)
async def get_vehicle(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
    enterprise_service: EnterpriseService = dep_enterprise_service,
):
    vehicle = await service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    ensure_vehicle_visible(vehicle, visible_enterprise_ids)
    timezone_by_enterprise_id = enterprise_timezones(
        await enterprise_service.get(
            EnterpriseFilter(ids=[vehicle.enterprise_id], load_relations=False)
        )
    )
    return vehicle_out(vehicle, timezone_by_enterprise_id.get(vehicle.enterprise_id))


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
    enterprise_service: EnterpriseService = dep_enterprise_service,
):
    if visible_enterprise_ids is not None and payload.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    vehicle = await service.create(payload.to_domain_model())
    timezone_by_enterprise_id = enterprise_timezones(
        await enterprise_service.get(
            EnterpriseFilter(ids=[vehicle.enterprise_id], load_relations=False)
        )
    )
    return vehicle_out(vehicle, timezone_by_enterprise_id.get(vehicle.enterprise_id))


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
    enterprise_service: EnterpriseService = dep_enterprise_service,
):
    current = await service.get_by_id(id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    ensure_vehicle_visible(current, visible_enterprise_ids)

    updated = await service.update(
        id,
        payload.apply_to_domain_model(current),
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    timezone_by_enterprise_id = enterprise_timezones(
        await enterprise_service.get(
            EnterpriseFilter(ids=[updated.enterprise_id], load_relations=False)
        )
    )
    return vehicle_out(updated, timezone_by_enterprise_id.get(updated.enterprise_id))


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
