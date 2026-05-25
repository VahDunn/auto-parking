from dataclasses import dataclass


@dataclass(slots=True)
class VehicleFilter:
    id: list[int] | None = None
    enterprise_ids: list[int] | None = None
    driver_id: int | None = None
    limit: int | None = 50
    offset: int | None = 0
    sort_by: str | None = None
