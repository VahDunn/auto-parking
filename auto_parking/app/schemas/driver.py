from pydantic import Field

from auto_parking.app.schemas.base import ApiSchema


class DriverOut(ApiSchema):
    id: int
    name: str
    salary_rub: int
    enterprise_id: int
    vehicles: list[int] = Field(default_factory=list)
    active_vehicle_id: int = -1
