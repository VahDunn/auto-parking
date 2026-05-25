from dataclasses import dataclass

from auto_parking.filter.base import BaseFilter


@dataclass(slots=True)
class DriverFilter(BaseFilter):
    id: list[int] | None = None
    enterprise_ids: list[int] | None = None
    vehicle_id: int | None = None
