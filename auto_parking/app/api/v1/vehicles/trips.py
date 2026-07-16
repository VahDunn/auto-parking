from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from auto_parking.app.api.v1.vehicles.common import (
    dep_actor_guard,
    dep_visible_ids,
    ensure_aware_datetime,
    ensure_valid_date_range,
    trip_out,
)
from auto_parking.app.deps.services import (
    dep_gpx_import_service,
    dep_trip_service,
    dep_vehicle_service,
)
from auto_parking.app.deps.visibility import ensure_enterprise_visible
from auto_parking.app.schemas.trip import TripOut
from auto_parking.app.service.trip import TripService
from auto_parking.app.service.vehicle import VehicleService

if TYPE_CHECKING:
    from auto_parking.app.service.gpx_import import GpxImportService

router = APIRouter()


@router.get(
    "/{id}/trips",
    response_model=list[TripOut],
    dependencies=[dep_actor_guard],
)
async def get_vehicle_trips(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    include_addresses: bool = Query(True),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: TripService = dep_trip_service,
):
    ensure_aware_datetime(date_from, "date_from")
    ensure_aware_datetime(date_to, "date_to")
    ensure_valid_date_range(date_from, date_to)

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    try:
        return [
            trip_out(trip)
            for trip in await service.get_vehicle_trips_in_range(
                vehicle_id=id,
                date_from=date_from,
                date_to=date_to,
                include_addresses=include_addresses,
            )
        ]
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


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
    service: "GpxImportService" = dep_gpx_import_service,
):
    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    if not file.filename or not file.filename.lower().endswith(".gpx"):
        raise HTTPException(status_code=400, detail="Only .gpx files are supported")

    raw_gpx = await file.read()

    if not raw_gpx:
        raise HTTPException(status_code=400, detail="GPX file is empty")

    try:
        trip_id = await service.import_vehicle_trip(
            vehicle_id=id,
            raw_gpx=raw_gpx,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    trip = await trip_service.get_by_id(trip_id)

    if trip is None:
        raise HTTPException(status_code=500, detail="Imported trip was not found")

    return trip_out(trip)
