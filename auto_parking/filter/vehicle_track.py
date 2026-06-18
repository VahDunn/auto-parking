from dataclasses import dataclass
from datetime import datetime

from auto_parking.filter.base import BaseFilter


@dataclass(slots=True)
class VehicleTrackFilter(BaseFilter):
    vehicle_id: int | None = None
    vehicle_ids: list[int] | None = None
    recorded_from: datetime | None = None
    recorded_to: datetime | None = None
    intervals: list[tuple[datetime, datetime]] | None = None
    trip_started_from: datetime | None = None
    trip_ended_to: datetime | None = None
