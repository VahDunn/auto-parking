from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class VehicleCreateModel(DomainModel):
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


@dataclass(slots=True)
class VehicleUpdateModel(DomainModel):
    changes: dict[str, Any]


@dataclass(slots=True)
class VehicleModel(DomainModel):
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
    drivers: list[int] = field(default_factory=list)
    active_driver_id: int = -1
    purchased_at_utc: datetime | None = None
    purchased_at_enterprise: datetime | None = None
    enterprise_timezone: str = "UTC"
