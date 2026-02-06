from pydantic import BaseModel


class EnterpriseOut(BaseModel):
    id: int
    name: str
    settlement: str
    vehicles: list[int] = []
    drivers: list[int] = []
