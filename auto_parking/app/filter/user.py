from dataclasses import dataclass, field

from auto_parking.app.filter.base import BaseFilter
from auto_parking.core.domain.enums import UserRole


@dataclass(slots=True)
class UserFilter(BaseFilter):
    ids: list[int] = field(default_factory=list)
    username: str = ""
    role: UserRole | None = None
    enterprise_id: int | None = None
