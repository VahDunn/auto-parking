from dataclasses import dataclass, field


@dataclass(slots=True)
class UserFilter:
    ids: list[int] = field(default_factory=list)
    username: str = ""
