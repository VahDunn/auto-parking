from dataclasses import dataclass, field
from datetime import datetime

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class VehicleModel(DomainModel):
    id: int | None
    price: int
    mileage: int
    vehicle_number: str
    owners_count: int
    accident_number: int
    manufacture_year: int
    model_id: int
    enterprise_id: int
    color: str
    drivers: list[int] = field(default_factory=list)
    active_driver_id: int | None = None
    purchased_at_utc: datetime | None = None
    enterprise_timezone: str | None = None
