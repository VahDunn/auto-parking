from fastapi import APIRouter, Depends, HTTPException, Query, status

from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleFilter, VehicleOut, VehicleUpdate
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.commons import dep_query
from auto_parking.deps.services import dep_vehicle_service
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.service.vehicle import VehicleService

router = APIRouter()


def _apply_enterprise_visibility(
    enterprise_ids: list[int] | None,
    visible_enterprise_ids: set[int] | None,
) -> list[int] | None:
    if visible_enterprise_ids is None:
        return enterprise_ids
    if enterprise_ids is None:
        return list(visible_enterprise_ids)
    return list(set(enterprise_ids) & visible_enterprise_ids)


def _ensure_vehicle_visible(vehicle: VehicleOut, visible_enterprise_ids: set[int] | None) -> None:
    if visible_enterprise_ids is not None and vehicle.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


dep_actor_guard = Depends(require_manager_or_higher)  # TODO здесь осторожно
dep_visible_ids = Depends(get_visible_enterprise_ids)


@router.get("", response_model=list[VehicleOut])
async def get_vehicles(
    id: list[int] | None = dep_query,
    enterprise_ids: list[int] | None = dep_query,
    driver_id: int | None = dep_query,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    enterprise_ids = _apply_enterprise_visibility(enterprise_ids, visible_enterprise_ids)
    if visible_enterprise_ids is not None and enterprise_ids == []:
        return []

    return await service.get(
        VehicleFilter(
            id=id,
            enterprise_ids=enterprise_ids,
            driver_id=driver_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{id}", response_model=VehicleOut)
async def get_vehicle(
    id: int,
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    vehicle = await service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    _ensure_vehicle_visible(vehicle, visible_enterprise_ids)
    return vehicle


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    if visible_enterprise_ids is not None and payload.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return await service.create(payload)


@router.patch("/{id}", response_model=VehicleOut)
async def update_vehicle(
    id: int,
    payload: VehicleUpdate,
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    current = await service.get_by_id(id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    _ensure_vehicle_visible(current, visible_enterprise_ids)

    data = payload.model_dump(exclude_unset=True)
    if "enterprise_id" in data and visible_enterprise_ids is not None:
        if data["enterprise_id"] not in visible_enterprise_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    updated = await service.update(id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return updated


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    id: int,
    actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    current = await service.get_by_id(id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    _ensure_vehicle_visible(current, visible_enterprise_ids)

    ok = await service.delete(id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return
