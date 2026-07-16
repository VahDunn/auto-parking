from dataclasses import dataclass

from auto_parking.app.filter.base import BaseFilter


@dataclass(slots=True)
class EnterpriseFilter(BaseFilter):
    ids: list[int] | None = None
