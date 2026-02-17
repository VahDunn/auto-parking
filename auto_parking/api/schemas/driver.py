from pydantic import BaseModel, Field


class DriverOut(BaseModel):
    id: int
    name: str
    salary_rub: int
    enterprise_id: int
    vehicles: list[int] = Field(default_factory=list)
    active_vehicle_id: int = -1


class DriverFilter(BaseModel):
    id: list[int] | None = None
    enterprise_ids: list[int] | None = None
    vehicle_id: int | None = None
