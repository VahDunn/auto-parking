from pydantic import BaseModel, ConfigDict

from auto_parking.api.schemas.driver import DriverShort


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
    enterprise_id: int
    drivers: list[DriverShort] | None = None
    active_driver_id: int | None = None
    active_driver: DriverShort | None = None


class VehicleShort(BaseModel):
    id: int
    vehicle_number: str
    model_id: int | None = None
    drivers: list[DriverShort] | None = None
    active_driver: DriverShort | None = None
