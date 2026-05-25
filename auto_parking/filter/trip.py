from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TripFilter:
    vehicle_id: int | None = None
    vehicle_ids: list[int] | None = None

    started_from: datetime | None = None
    started_to: datetime | None = None
    ended_from: datetime | None = None
    ended_to: datetime | None = None

    limit: int | None = 100
    offset: int | None = 0
    sort_by: str | None = None
