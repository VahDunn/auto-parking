from dataclasses import dataclass


@dataclass(slots=True)
class DriverFilter:
    id: list[int] | None = None
    enterprise_ids: list[int] | None = None
    vehicle_id: int | None = None
