from dataclasses import dataclass

from auto_parking.app.filter.base import BaseFilter


@dataclass(slots=True)
class VehicleModelFilter(BaseFilter):
    ids: list[int] | None = None
    name: str | None = None
