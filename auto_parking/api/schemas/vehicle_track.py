from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class TrackFormat(str, Enum):
    json = "json"
    geojson = "geojson"


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware (with timezone)")
    return dt


class VehicleTrackPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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


class VehicleTrackQuery(BaseModel):
    date_from: datetime
    date_to: datetime
    format: TrackFormat = TrackFormat.json

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: list[float]


class GeoJSONFeature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str
    features: list[GeoJSONFeature]
