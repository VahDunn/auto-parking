from pydantic import BaseModel


class DriverOut(BaseModel):
    id: int
    name: str
    salary_rub: int
    enterprise_id: int
    vehicles: list[int] = []
    active_vehicle_id: int = -1


class DriverFilter(BaseModel):
    id: list[int] | None = None
    enterprise_id: int | None = None
    vehicle_id: int | None = None
