from datetime import datetime

from pydantic import field_validator

from auto_parking.app.schemas.base import ApiSchema
from auto_parking.app.schemas.vehicle_track import GeoJSONFeatureCollection, VehicleTrackPointOut


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware (with timezone)")
    return dt


class TripTrackGroupOut(ApiSchema):
    trip_id: int
    vehicle_id: int

    started_at_utc: datetime
    ended_at_utc: datetime

    started_at_enterprise: datetime
    ended_at_enterprise: datetime
    enterprise_timezone: str = "UTC"

    points: list[VehicleTrackPointOut] | None = None
    track: GeoJSONFeatureCollection | None = None

    @field_validator(
        "started_at_utc",
        "ended_at_utc",
        "started_at_enterprise",
        "ended_at_enterprise",
    )
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)
