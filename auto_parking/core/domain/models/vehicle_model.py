from dataclasses import dataclass

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class VehicleModelInfo(DomainModel):
    id: int | None
    name: str
    type: str
    horse_powers: int
    seats_number: int
    fuel_capacity_liters: int
