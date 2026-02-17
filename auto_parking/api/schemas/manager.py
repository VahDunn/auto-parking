from pydantic import BaseModel, Field


class ManagerFilter(BaseModel):
    ids: list[int] = Field(default_factory=list)
    username: str = Field(default_factory=str)
