from pydantic import BaseModel


class EnterpriseOut(BaseModel):
    id: int
    name: str
    settlement: str
    vehicles: list[int] | None = None
    drivers: list[int] | None = None
