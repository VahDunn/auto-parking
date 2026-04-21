from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int

    started_at_utc: datetime
    ended_at_utc: datetime

    started_at_enterprise: datetime
    ended_at_enterprise: datetime
    enterprise_timezone: str = "UTC"


class TripFilter(BaseModel):
    vehicle_id: int | None = None
    vehicle_ids: list[int] | None = None

    started_from: datetime | None = None
    started_to: datetime | None = None
    ended_from: datetime | None = None
    ended_to: datetime | None = None

    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str | None = None


class TripCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_id: int
    started_at: datetime
    ended_at: datetime

    @field_validator("started_at", "ended_at")
    @classmethod
    def validate_aware_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware (with timezone)")
        return v

    @field_validator("ended_at")
    @classmethod
    def validate_range(cls, v: datetime, info) -> datetime:
        started_at = info.data.get("started_at")
        if started_at is not None and v < started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        return v


class TripUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    started_at: datetime | None = None
    ended_at: datetime | None = None

    @field_validator("started_at", "ended_at")
    @classmethod
    def validate_aware_datetime(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware (with timezone)")
        return v
