from pydantic import BaseModel


class DriverOut(BaseModel):
    id: int
    name: str
    salary_rub: int
    enterprise_id: int
    vehicles: list[int] | None = None
    active_vehicle_id: int | None = None


class DriverFilter(BaseModel):
    ids: list[int] | None = None
    enterprise_id: int | None = None
