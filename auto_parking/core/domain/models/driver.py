from dataclasses import dataclass, field

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class DriverModel(DomainModel):
    id: int
    name: str
    salary_rub: int
    enterprise_id: int
    vehicles: list[int] = field(default_factory=list)
    active_vehicle_id: int | None = -1
