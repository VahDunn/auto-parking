import json
from datetime import datetime
from typing import TYPE_CHECKING

from auto_parking.core.domain.enums import TrackFormat
from auto_parking.core.domain.models import (
    GeoJSONFeatureCollectionModel,
    GeoJSONFeatureModel,
    GeoJSONGeometryModel,
    VehicleTrackPointModel,
)
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc

if TYPE_CHECKING:
    from auto_parking.db.models import Vehicle
    from auto_parking.repo.vehicle import VehicleRepository
    from auto_parking.repo.vehicle_track import VehicleTrackRepository


class VehicleTrackService:
    def __init__(
        self,
        vehicle_repo: "VehicleRepository",
        track_repo: "VehicleTrackRepository",
    ) -> None:
        self._vehicle_repo = vehicle_repo
        self._track_repo = track_repo

    async def get_track(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
        format: TrackFormat,
    ) -> tuple[
        list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel | None,
        "Vehicle | None",
    ]:
        vehicle = await self._vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            return None, None

        enterprise = vehicle.enterprise
        enterprise_tz = enterprise.timezone if enterprise and enterprise.timezone else "UTC"

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        rows = await self._track_repo.get_points(
            vehicle_id=vehicle_id,
            date_from_utc=date_from_utc,
            date_to_utc=date_to_utc,
        )

        if format == TrackFormat.geojson:
            features: list[GeoJSONFeatureModel] = []

            for row in rows:
                raw_geometry = json.loads(row.geojson)

                geometry = GeoJSONGeometryModel(
                    type=raw_geometry["type"],
                    coordinates=raw_geometry["coordinates"],
                )

                feature = GeoJSONFeatureModel(
                    type="Feature",
                    geometry=geometry,
                    properties={
                        "vehicle_id": vehicle_id,
                        "recorded_at_utc": row.recorded_at_utc.isoformat(),
                        "recorded_at_enterprise": to_enterprise_tz(
                            row.recorded_at_utc,
                            enterprise_tz,
                        ).isoformat(),
                        "enterprise_timezone": enterprise_tz,
                    },
                )
                features.append(feature)

            return (
                GeoJSONFeatureCollectionModel(
                    type="FeatureCollection",
                    features=features,
                ),
                vehicle,
            )

        return (
            [
                VehicleTrackPointModel(
                    id=vehicle_id,
                    recorded_at_utc=row.recorded_at_utc,
                    recorded_at_enterprise=to_enterprise_tz(
                        row.recorded_at_utc,
                        enterprise_tz,
                    ),
                    latitude=row.latitude,
                    longitude=row.longitude,
                )
                for row in rows
            ],
            vehicle,
        )
