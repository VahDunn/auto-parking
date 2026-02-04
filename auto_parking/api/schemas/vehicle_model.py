from pydantic import BaseModel


class VehicleModelOut(BaseModel):
    id: int
    name: str
    type: str
    horse_powers: int
    seats_number: int
    fuel_capacity_liters: int
