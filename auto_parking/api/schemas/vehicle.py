from pydantic import BaseModel, ConfigDict


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
