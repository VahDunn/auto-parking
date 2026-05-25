from datetime import datetime
from typing import ClassVar

from pydantic import ConfigDict, field_validator

from auto_parking.api.schemas.base import ApiSchema


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware (with timezone)")
    return dt


class TripPointOut(ApiSchema):
    id: int
    recorded_at_utc: datetime
    recorded_at_enterprise: datetime
    latitude: float
    longitude: float
    address: str | None = None

    @field_validator("recorded_at_utc", "recorded_at_enterprise")
    @classmethod
    def validate_aware_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class TripOut(ApiSchema):
    id: int
    vehicle_id: int

    started_at_utc: datetime
    ended_at_utc: datetime

    started_at_enterprise: datetime
    ended_at_enterprise: datetime
    enterprise_timezone: str = "UTC"

    start_point: TripPointOut
    end_point: TripPointOut

    @field_validator(
        "started_at_utc",
        "ended_at_utc",
        "started_at_enterprise",
        "ended_at_enterprise",
    )
    @classmethod
    def validate_aware_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class TripCreate(ApiSchema):
    vehicle_id: int
    started_at: datetime
    ended_at: datetime
    start_point_id: int
    end_point_id: int

    @field_validator("started_at", "ended_at")
    @classmethod
    def validate_aware_datetime(cls, v: datetime) -> datetime:
        return _ensure_aware(v)

    @field_validator("ended_at")
    @classmethod
    def validate_range(cls, v: datetime, info) -> datetime:
        started_at = info.data.get("started_at")
        if started_at is not None and v < started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        return v


class TripUpdate(ApiSchema):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    started_at: datetime | None = None
    ended_at: datetime | None = None
    start_point_id: int | None = None
    end_point_id: int | None = None

    @field_validator("started_at", "ended_at")
    @classmethod
    def validate_aware_datetime(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return _ensure_aware(v)
