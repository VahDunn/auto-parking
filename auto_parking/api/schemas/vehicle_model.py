from auto_parking.api.schemas.base import ApiSchema


class VehicleModelOut(ApiSchema):
    id: int
    name: str
    type: str
    horse_powers: int
    seats_number: int
    fuel_capacity_liters: int
