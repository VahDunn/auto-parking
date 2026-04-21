from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auto_parking.api.schemas.trip import TripOut
from auto_parking.api.schemas.trip_track import TripTrackGroupOut
from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleFilter, VehicleOut, VehicleUpdate
from auto_parking.api.schemas.vehicle_track import (
    GeoJSONFeatureCollection,
    TrackFormat,
    VehicleTrackPointOut,
)
from auto_parking.core.errors import NotFoundError
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.commons import dep_query
from auto_parking.deps.services import (
    dep_trip_service,
    dep_trip_track_service,
    dep_vehicle_service,
    dep_vehicle_track_service,
)
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.service.trip import TripService
from auto_parking.service.trip_track import TripTrackService
from auto_parking.service.vehicle import VehicleService
from auto_parking.service.vehicle_track import VehicleTrackService

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


def _ensure_enterprise_visible(
    enterprise_id: int,
    visible_enterprise_ids: set[int] | None,
) -> None:
    if visible_enterprise_ids is not None and enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


@router.get(
    "",
    response_model=list[VehicleOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicles(
    id: list[int] | None = dep_query,
    enterprise_ids: list[int] | None = dep_query,
    driver_id: int | None = dep_query,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
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
            sort_by=sort_by,
        )
    )


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

    _ensure_vehicle_visible(vehicle, visible_enterprise_ids)
    return vehicle


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

    return await service.create(payload)


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

    _ensure_vehicle_visible(current, visible_enterprise_ids)

    data = payload.model_dump(exclude_unset=True)
    if "enterprise_id" in data and visible_enterprise_ids is not None:
        if data["enterprise_id"] not in visible_enterprise_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    updated = await service.update(id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return updated


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

    _ensure_vehicle_visible(current, visible_enterprise_ids)

    ok = await service.delete(id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return


@router.get(
    "/{id}/trips",
    response_model=list[TripOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicle_trips(
    id: int,
    date_from: datetime = Query(..., description="Timezone-aware datetime"),
    date_to: datetime = Query(..., description="Timezone-aware datetime"),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: TripService = dep_trip_service,
):
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    try:
        return await service.get_vehicle_trips_in_range(
            vehicle_id=id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/{id}/track",
    response_model=list[VehicleTrackPointOut] | GeoJSONFeatureCollection,
    dependencies=[dep_actor_guard],
)
async def get_vehicle_track(
    id: int,
    date_from: datetime = Query(..., description="Timezone-aware datetime"),
    date_to: datetime = Query(..., description="Timezone-aware datetime"),
    format: TrackFormat = Query(TrackFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleTrackService = dep_vehicle_track_service,
):
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )

    try:
        result, vehicle = await service.get_track(
            vehicle_id=id,
            date_from=date_from,
            date_to=date_to,
            format=format,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)
    return result


@router.get(
    "/{id}/track-by-trips",
    response_model=list[TripTrackGroupOut]
    | list[VehicleTrackPointOut]
    | GeoJSONFeatureCollection
    | list[dict[str, Any]],
    dependencies=[dep_actor_guard],
)
async def get_vehicle_track_by_trips(
    id: int,
    date_from: datetime = Query(..., description="Timezone-aware datetime"),
    date_to: datetime = Query(..., description="Timezone-aware datetime"),
    format: TrackFormat = Query(TrackFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: TripTrackService = dep_trip_track_service,
):
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    try:
        result = await service.get_track(
            vehicle_id=id,
            date_from=date_from,
            date_to=date_to,
            format=format,
        )

    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err.message,
        ) from err
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return result
