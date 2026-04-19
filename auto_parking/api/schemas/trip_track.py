from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware (with timezone)")
    return dt


class TripTrackPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recorded_at_utc: datetime
    recorded_at_enterprise: datetime
    latitude: float
    longitude: float

    @field_validator("recorded_at_utc", "recorded_at_enterprise")
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class TripTrackGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trip_id: int
    vehicle_id: int

    started_at_utc: datetime
    ended_at_utc: datetime

    started_at_enterprise: datetime
    ended_at_enterprise: datetime
    enterprise_timezone: str = "UTC"

    points: list[TripTrackPointOut]

    @field_validator(
        "started_at_utc",
        "ended_at_utc",
        "started_at_enterprise",
        "ended_at_enterprise",
    )
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)
