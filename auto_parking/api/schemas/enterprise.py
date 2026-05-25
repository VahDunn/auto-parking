from pydantic import BaseModel, Field


class EnterpriseOut(BaseModel):
    id: int
    name: str
    settlement: str
    vehicles: list[int] = Field(default_factory=list)
    drivers: list[int] = Field(default_factory=list)
    managers: list[int] = Field(default_factory=list)
    timezone: str | None = None  # 👈 вот это
