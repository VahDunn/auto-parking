from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class VehicleTrackPointModel(DomainModel):
    id: int | None
    recorded_at_utc: datetime
    recorded_at_enterprise: datetime
    latitude: float
    longitude: float
    trip_id: int | None = None


@dataclass(slots=True)
class GeoJSONGeometryModel(DomainModel):
    type: str
    coordinates: list[float]


@dataclass(slots=True)
class GeoJSONFeatureModel(DomainModel):
    type: str
    geometry: GeoJSONGeometryModel
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GeoJSONFeatureCollectionModel(DomainModel):
    type: str
    features: list[GeoJSONFeatureModel] = field(default_factory=list)


@dataclass(slots=True)
class TripTrackGroupModel(DomainModel):
    trip_id: int | None
    vehicle_id: int | None
    started_at_utc: datetime
    ended_at_utc: datetime
    started_at_enterprise: datetime
    ended_at_enterprise: datetime
    enterprise_timezone: str = "UTC"
    points: list[VehicleTrackPointModel] | None = None
    track: GeoJSONFeatureCollectionModel | None = None
