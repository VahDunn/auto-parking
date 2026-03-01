from pydantic import BaseModel, Field


class UserFilter(BaseModel):
    ids: list[int] = Field(default_factory=list)
    username: str = Field(default_factory=str)
