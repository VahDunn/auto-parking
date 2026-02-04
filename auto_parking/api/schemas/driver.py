from pydantic import BaseModel


class DriverOut(BaseModel):
    id: int
    name: str
    salary_rub: int
    enterprise_id: int
