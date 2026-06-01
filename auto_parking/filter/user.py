from dataclasses import dataclass, field

from auto_parking.core.domain.enums import UserRole
from auto_parking.filter.base import BaseFilter


@dataclass(slots=True)
class UserFilter(BaseFilter):
    ids: list[int] = field(default_factory=list)
    username: str = ""
    role: UserRole | None = None
    enterprise_id: int | None = None
