from datetime import datetime
from typing import Any

from pydantic import field_validator

from auto_parking.api.schemas.base import ApiSchema
from auto_parking.core.enums import TrackFormat


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware (with timezone)")
    return dt


class VehicleTrackPointOut(ApiSchema):
    id: int
    trip_id: int | None = None
    recorded_at_utc: datetime
    recorded_at_enterprise: datetime
    latitude: float
    longitude: float

    @field_validator("recorded_at_utc", "recorded_at_enterprise")
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class VehicleTrackQuery(ApiSchema):
    date_from: datetime
    date_to: datetime
    format: TrackFormat = TrackFormat.json

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class GeoJSONGeometry(ApiSchema):
    type: str
    coordinates: list[float]


class GeoJSONFeature(ApiSchema):
    type: str
    geometry: GeoJSONGeometry
    properties: dict[str, Any]


class GeoJSONFeatureCollection(ApiSchema):
    type: str
    features: list[GeoJSONFeature]
