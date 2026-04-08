import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

PLATE_RE = re.compile(r"^(?i:[АВЕКМНОРСТУХ])\d{3}(?i:[АВЕКМНОРСТУХ]){2}\d{2,3}$")


def is_valid_plate(s: str) -> bool:
    return bool(PLATE_RE.fullmatch(s.strip()))


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price: int
    mileage: int
    vehicle_number: str
    owners_count: int
    accident_number: int
    manufacture_year: int
    model_id: int
    color: str
    enterprise_id: int
    drivers: list[int] = Field(default_factory=list)
    active_driver_id: int = -1

    purchased_at_utc: datetime | None = None
    purchased_at_enterprise: datetime | None = None
    enterprise_timezone: str = "UTC"

    @field_validator("drivers", mode="before")
    @classmethod
    def drivers_to_ids(cls, v):
        if v is None:
            return []
        if v and not isinstance(v[0], int):
            return [d.id for d in v]
        return v

    @field_validator("active_driver_id", mode="before")
    @classmethod
    def none_to_minus_one(cls, v):
        return v if v is not None else -1


class VehicleFilter(BaseModel):
    id: list[int] | None = None
    enterprise_ids: list[int] | None = None
    driver_id: int | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str | None = None


class VehicleCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: int
    mileage: int
    vehicle_number: str
    owners_count: int
    accident_number: int
    manufacture_year: int
    model_id: int
    enterprise_id: int
    color: str
    purchased_at: datetime

    @field_validator("purchased_at")
    @classmethod
    def validate_datetime(cls, v: datetime):
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware (with timezone)")
        return v


class VehicleUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: int | None = None
    mileage: int | None = None
    vehicle_number: str | None = None
    owners_count: int | None = None
    accident_number: int | None = None
    manufacture_year: int | None = None
    model_id: int | None = None
    enterprise_id: int | None = None
    active_driver_id: int | None = None
    color: str | None = None
    purchased_at: datetime | None = None

    @field_validator("purchased_at")
    @classmethod
    def validate_datetime(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware (with timezone)")
        return v
