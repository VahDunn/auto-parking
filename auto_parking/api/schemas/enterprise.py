from pydantic import BaseModel


class EnterpriseOut(BaseModel):
    id: int
    name: str
    settlement: str
