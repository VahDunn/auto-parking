from dataclasses import dataclass


@dataclass(slots=True)
class EnterpriseFilter:
    ids: list[int] | None = None
