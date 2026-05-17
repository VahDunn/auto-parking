from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from auto_parking.api.schemas.trip import TripOut
from auto_parking.api.schemas.trip_track import TripTrackGroupOut
from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleFilter, VehicleOut, VehicleUpdate
from auto_parking.api.schemas.vehicle_track import (
    GeoJSONFeatureCollection,
    TrackFormat,
    VehicleTrackPointOut,
)
from auto_parking.core.domain.import_export_format import ExportFormat
from auto_parking.core.errors import NotFoundError
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import (
    dep_export_service,
    dep_trip_service,
    dep_trip_track_service,
    dep_vehicle_service,
    dep_vehicle_track_service,
    dep_gpx_import_service,
)
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.service.trip import TripService
from auto_parking.service.trip_track import TripTrackService
from auto_parking.service.vehicle import VehicleService
from auto_parking.service.vehicle_track import VehicleTrackService

if TYPE_CHECKING:
    from auto_parking.service.export import ExportService

router = APIRouter()


def _parse_int_list(value: str | None) -> list[int] | None:
    if value is None or value.strip() == "":
        return None

    return [int(item.strip()) for item in value.split(",") if item.strip()]


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


def _ensure_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be timezone-aware",
        )


def _export_response(
    *,
    content: str,
    format: ExportFormat,
    filename_base: str,
) -> Response:
    if format == ExportFormat.csv:
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
    )


dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


@router.get(
    "",
    response_model=list[VehicleOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicles(
    id: str | None = Query(None),
    enterprise_ids: str | None = Query(None),
    driver_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleService = dep_vehicle_service,
):
    parsed_ids = _parse_int_list(id)
    parsed_enterprise_ids = _parse_int_list(enterprise_ids)

    parsed_enterprise_ids = _apply_enterprise_visibility(
        parsed_enterprise_ids,
        visible_enterprise_ids,
    )

    if visible_enterprise_ids is not None and parsed_enterprise_ids == []:
        return []

    return await service.get(
        VehicleFilter(
            id=parsed_ids,
            enterprise_ids=parsed_enterprise_ids,
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


@router.get(
    "/{id}/export-trips",
    dependencies=[dep_actor_guard],
)
async def export_vehicle_trips(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    format: ExportFormat = Query(ExportFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: "ExportService" = dep_export_service,
):
    _ensure_aware_datetime(date_from, "date_from")
    _ensure_aware_datetime(date_to, "date_to")

    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    content = await service.export_vehicle_trips(
        vehicle_id=id,
        date_from=date_from,
        date_to=date_to,
        format=format,
    )

    return _export_response(
        content=content,
        format=format,
        filename_base=f"vehicle_{id}_trips_export",
    )


@router.get(
    "/{id}/trips",
    response_model=list[TripOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicle_trips(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: TripService = dep_trip_service,
):
    _ensure_aware_datetime(date_from, "date_from")
    _ensure_aware_datetime(date_to, "date_to")

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    return await service.get_vehicle_trips_in_range(
        vehicle_id=id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/{id}/track",
    response_model=list[VehicleTrackPointOut] | GeoJSONFeatureCollection,
    dependencies=[dep_actor_guard],
)
async def get_vehicle_track(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    format: TrackFormat = Query(TrackFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: VehicleTrackService = dep_vehicle_track_service,
):
    _ensure_aware_datetime(date_from, "date_from")
    _ensure_aware_datetime(date_to, "date_to")

    result, vehicle = await service.get_track(
        vehicle_id=id,
        date_from=date_from,
        date_to=date_to,
        format=format,
    )

    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)
    return result


@router.get(
    "/{id}/track-by-trips",
    response_model=list[TripTrackGroupOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicle_track_by_trips(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    format: TrackFormat = Query(TrackFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: TripTrackService = dep_trip_track_service,
):
    _ensure_aware_datetime(date_from, "date_from")
    _ensure_aware_datetime(date_to, "date_to")

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    return await service.get_grouped_track(
        vehicle_id=id,
        date_from=date_from,
        date_to=date_to,
        format=format,
    )

@router.post(
    "/{id}/trips/import-gpx",
    response_model=TripOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[dep_actor_guard],
)
async def import_vehicle_trip_gpx(
    id: int,
    file: UploadFile = File(...),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    trip_service: TripService = dep_trip_service,
    service: GpxImportService = dep_gpx_import_service,
):
    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    _ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    if not file.filename or not file.filename.lower().endswith(".gpx"):
        raise HTTPException(status_code=400, detail="Only .gpx files are supported")

    raw_gpx = await file.read()

    if not raw_gpx:
        raise HTTPException(status_code=400, detail="GPX file is empty")

    try:
        trip = await service.import_vehicle_trip(
            vehicle_id=id,
            raw_gpx=raw_gpx,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    trip_out = await trip_service.get_by_id(trip.id)

    if trip_out is None:
        raise HTTPException(status_code=500, detail="Imported trip was not found")

    return trip_out
