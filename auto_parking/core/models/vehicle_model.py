from dataclasses import dataclass

from auto_parking.core.models.base import DomainModel


@dataclass(slots=True)
class VehicleModelInfo(DomainModel):
    id: int
    name: str
    type: str
    horse_powers: int
    seats_number: int
    fuel_capacity_liters: int
