import re
from datetime import datetime

from pydantic import Field, field_validator

from auto_parking.app.schemas.base import ApiSchema
from auto_parking.core.domain.models import VehicleModel
from auto_parking.core.utils.datetime import to_utc

PLATE_RE = re.compile(r"^(?i:[АВЕКМНОРСТУХ])\d{3}(?i:[АВЕКМНОРСТУХ]){2}\d{2,3}$")


def is_valid_plate(s: str) -> bool:
    return bool(PLATE_RE.fullmatch(s.strip()))


def normalize_plate(s: str) -> str:
    return s.strip().upper()


class VehicleOut(ApiSchema):
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


class VehicleCreate(ApiSchema):
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

    @field_validator("vehicle_number")
    @classmethod
    def validate_vehicle_number(cls, v: str) -> str:
        normalized = normalize_plate(v)
        if not is_valid_plate(normalized):
            raise ValueError("Invalid vehicle number")
        return normalized

    def to_domain_model(self) -> VehicleModel:
        return VehicleModel(
            id=None,
            price=self.price,
            mileage=self.mileage,
            vehicle_number=self.vehicle_number,
            owners_count=self.owners_count,
            accident_number=self.accident_number,
            manufacture_year=self.manufacture_year,
            model_id=self.model_id,
            enterprise_id=self.enterprise_id,
            color=self.color,
            purchased_at_utc=to_utc(self.purchased_at),
        )


class VehicleUpdate(ApiSchema):
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

    @field_validator("vehicle_number")
    @classmethod
    def validate_vehicle_number(cls, v: str | None) -> str | None:
        if v is None:
            return v

        normalized = normalize_plate(v)
        if not is_valid_plate(normalized):
            raise ValueError("Invalid vehicle number")
        return normalized

    def apply_to_domain_model(self, vehicle: VehicleModel) -> VehicleModel:
        data = vehicle.to_dict()
        changes = self.model_dump(exclude_unset=True)

        if "purchased_at" in changes:
            data["purchased_at_utc"] = to_utc(changes.pop("purchased_at"))

        data.update(changes)
        return VehicleModel(**data)
