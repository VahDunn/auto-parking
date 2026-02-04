from pydantic import BaseModel

from auto_parking.api.schemas.vehicle import VehicleShort


class EnterpriseOut(BaseModel):
    id: int
    name: str
    settlement: str
    vehicles: list[VehicleShort] | None = None
