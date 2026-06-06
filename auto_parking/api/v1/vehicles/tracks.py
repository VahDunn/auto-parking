from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from auto_parking.api.schemas.trip_track import TripTrackGroupOut
from auto_parking.api.schemas.vehicle_track import (
    GeoJSONFeatureCollection,
    TrackFormat,
    VehicleTrackPointOut,
)
from auto_parking.api.v1.vehicles.common import (
    dep_actor_guard,
    dep_visible_ids,
    ensure_aware_datetime,
    ensure_enterprise_visible,
    ensure_valid_date_range,
    enterprise_timezones,
    track_response_out,
    trip_track_group_out,
)
from auto_parking.deps.services import (
    dep_enterprise_service,
    dep_trip_track_service,
    dep_vehicle_service,
    dep_vehicle_track_service,
)
from auto_parking.filter import EnterpriseFilter
from auto_parking.service.enterprise import EnterpriseService
from auto_parking.service.trip_track import TripTrackService
from auto_parking.service.vehicle import VehicleService
from auto_parking.service.vehicle_track import VehicleTrackService

router = APIRouter()


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
    vehicle_service: VehicleService = dep_vehicle_service,
    enterprise_service: EnterpriseService = dep_enterprise_service,
    service: VehicleTrackService = dep_vehicle_track_service,
):
    ensure_aware_datetime(date_from, "date_from")
    ensure_aware_datetime(date_to, "date_to")
    ensure_valid_date_range(date_from, date_to)

    vehicle = await vehicle_service.get_by_id(id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)
    timezone_by_enterprise_id = enterprise_timezones(
        await enterprise_service.get(
            EnterpriseFilter(ids=[vehicle.enterprise_id], load_relations=False)
        )
    )
    result = await service.get_track(
        vehicle_id=id,
        date_from=date_from,
        date_to=date_to,
        format=format,
        enterprise_timezone=timezone_by_enterprise_id.get(vehicle.enterprise_id) or "UTC",
    )
    return track_response_out(result)


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
    ensure_aware_datetime(date_from, "date_from")
    ensure_aware_datetime(date_to, "date_to")
    ensure_valid_date_range(date_from, date_to)

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    return [
        trip_track_group_out(group)
        for group in await service.get_grouped_track(
            vehicle_id=id,
            date_from=date_from,
            date_to=date_to,
            format=format,
        )
    ]
