from dataclasses import dataclass

from auto_parking.app.filter.base import BaseFilter


@dataclass(slots=True)
class VehicleFilter(BaseFilter):
    id: list[int] | None = None
    vehicle_number_prefix: str | None = None
    enterprise_ids: list[int] | None = None
    driver_id: int | None = None
    limit: int | None = 50
    offset: int | None = 0
    sort_by: str | None = None
