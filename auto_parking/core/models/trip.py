from dataclasses import dataclass
from datetime import datetime
from typing import Any

from auto_parking.core.models.base import DomainModel


@dataclass(slots=True)
class TripCreateModel(DomainModel):
    vehicle_id: int
    started_at: datetime
    ended_at: datetime
    start_point_id: int
    end_point_id: int


@dataclass(slots=True)
class TripUpdateModel(DomainModel):
    changes: dict[str, Any]


@dataclass(slots=True)
class TripPointModel(DomainModel):
    id: int
    recorded_at_utc: datetime
    recorded_at_enterprise: datetime
    latitude: float
    longitude: float
    address: str | None = None


@dataclass(slots=True)
class TripModel(DomainModel):
    id: int
    vehicle_id: int
    started_at_utc: datetime
    ended_at_utc: datetime
    started_at_enterprise: datetime
    ended_at_enterprise: datetime
    start_point: TripPointModel
    end_point: TripPointModel
    enterprise_timezone: str = "UTC"
