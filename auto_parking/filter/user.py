from dataclasses import dataclass, field

from auto_parking.filter.base import BaseFilter


@dataclass(slots=True)
class UserFilter(BaseFilter):
    ids: list[int] = field(default_factory=list)
    username: str = ""
