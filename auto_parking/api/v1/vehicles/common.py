from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.responses import Response

from auto_parking.api.schemas.trip import TripOut
from auto_parking.api.schemas.trip_track import TripTrackGroupOut
from auto_parking.api.schemas.vehicle import VehicleOut
from auto_parking.api.schemas.vehicle_track import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    VehicleTrackPointOut,
)
from auto_parking.core.domain.enums.import_export_format import ExportFormat
from auto_parking.core.domain.models import (
    EnterpriseModel,
    GeoJSONFeatureCollectionModel,
    GeoJSONFeatureModel,
    GeoJSONGeometryModel,
    TripModel,
    TripTrackGroupModel,
    VehicleModel,
    VehicleTrackPointModel,
)
from auto_parking.core.utils.datetime import to_enterprise_tz
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.visibility import (
    ensure_enterprise_visible,
    get_visible_enterprise_ids,
)

dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


def vehicle_out(vehicle: VehicleModel, enterprise_timezone: str | None) -> VehicleOut:
    purchased_at_utc = vehicle.purchased_at_utc
    data = vehicle.to_dict()
    model_enterprise_timezone = data.pop("enterprise_timezone", None)
    resolved_enterprise_timezone = enterprise_timezone or model_enterprise_timezone
    return VehicleOut(
        **data,
        purchased_at_enterprise=(
            to_enterprise_tz(purchased_at_utc, resolved_enterprise_timezone)
            if purchased_at_utc
            else None
        ),
        enterprise_timezone=resolved_enterprise_timezone or "UTC",
    )


def enterprise_timezones(enterprises: list[EnterpriseModel]) -> dict[int, str | None]:
    return {
        enterprise.id: enterprise.timezone
        for enterprise in enterprises
        if enterprise.id is not None
    }


def trip_out(trip: TripModel) -> TripOut:
    return TripOut(**trip.to_dict())


def track_point_out(point: VehicleTrackPointModel) -> VehicleTrackPointOut:
    return VehicleTrackPointOut(**point.to_dict())


def geojson_geometry_out(geometry: GeoJSONGeometryModel) -> GeoJSONGeometry:
    return GeoJSONGeometry(**geometry.to_dict())


def geojson_feature_out(feature: GeoJSONFeatureModel) -> GeoJSONFeature:
    return GeoJSONFeature(
        type=feature.type,
        geometry=geojson_geometry_out(feature.geometry),
        properties=feature.properties,
    )


def geojson_collection_out(collection: GeoJSONFeatureCollectionModel) -> GeoJSONFeatureCollection:
    return GeoJSONFeatureCollection(
        type=collection.type,
        features=[geojson_feature_out(feature) for feature in collection.features],
    )


def track_response_out(
    result: list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel,
) -> list[VehicleTrackPointOut] | GeoJSONFeatureCollection:
    if isinstance(result, GeoJSONFeatureCollectionModel):
        return geojson_collection_out(result)
    return [track_point_out(point) for point in result]


def trip_track_group_out(group: TripTrackGroupModel) -> TripTrackGroupOut:
    return TripTrackGroupOut(
        trip_id=group.trip_id,
        vehicle_id=group.vehicle_id,
        started_at_utc=group.started_at_utc,
        ended_at_utc=group.ended_at_utc,
        started_at_enterprise=group.started_at_enterprise,
        ended_at_enterprise=group.ended_at_enterprise,
        enterprise_timezone=group.enterprise_timezone,
        points=(
            [track_point_out(point) for point in group.points] if group.points is not None else None
        ),
        track=geojson_collection_out(group.track) if group.track is not None else None,
    )


def parse_int_list(value: str | None) -> list[int] | None:
    if value is None or value.strip() == "":
        return None

    return [int(item.strip()) for item in value.split(",") if item.strip()]


def ensure_vehicle_visible(vehicle: VehicleModel, visible_enterprise_ids: set[int] | None) -> None:
    ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)


def ensure_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be timezone-aware",
        )


def ensure_valid_date_range(date_from: datetime, date_to: datetime) -> None:
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")


def export_response(
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
