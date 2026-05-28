from dataclasses import dataclass
from datetime import datetime

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class TripPointModel(DomainModel):
    id: int | None
    recorded_at_utc: datetime
    recorded_at_enterprise: datetime
    latitude: float
    longitude: float
    address: str | None = None


@dataclass(slots=True)
class TripModel(DomainModel):
    id: int | None
    vehicle_id: int
    started_at_utc: datetime
    ended_at_utc: datetime
    start_point_id: int
    end_point_id: int
    started_at_enterprise: datetime | None = None
    ended_at_enterprise: datetime | None = None
    start_point: TripPointModel | None = None
    end_point: TripPointModel | None = None
    enterprise_timezone: str = "UTC"
