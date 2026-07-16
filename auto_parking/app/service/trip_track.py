from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

from auto_parking.app.filter import TripFilter, VehicleTrackFilter
from auto_parking.core.domain.enums import TrackFormat
from auto_parking.core.domain.models import (
    GeoJSONFeatureCollectionModel,
    GeoJSONFeatureModel,
    GeoJSONGeometryModel,
    TripTrackGroupModel,
    VehicleTrackPointModel,
)
from auto_parking.core.errors import NotFoundError
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc

if TYPE_CHECKING:
    from auto_parking.infrastructure.db.repositories.trip import TripRepository
    from auto_parking.infrastructure.db.repositories.vehicle import VehicleRepository
    from auto_parking.infrastructure.db.repositories.vehicle_track import VehicleTrackRepository


class TripTrackService:
    def __init__(
        self,
        vehicle_repo: "VehicleRepository",
        trip_repo: "TripRepository",
        track_repo: "VehicleTrackRepository",
    ) -> None:
        self._vehicle_repo = vehicle_repo
        self._trip_repo = trip_repo
        self._track_repo = track_repo

    async def get_track(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
        format: TrackFormat,
        enterprise_timezone: str | None = None,
    ) -> list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel:
        enterprise_tz = await self._enterprise_timezone(vehicle_id, enterprise_timezone)

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        trips = await self._trip_repo.get(
            TripFilter(
                vehicle_id=vehicle_id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=None,
                offset=None,
                load_relations=False,
            )
        )

        points_by_trip = await self._get_points_by_trip(vehicle_id, trips)
        flat_rows = [
            (row, trip.id)
            for trip in trips
            for row in points_by_trip[trip.id]
        ]

        if format == TrackFormat.geojson:
            return GeoJSONFeatureCollectionModel(
                type="FeatureCollection",
                features=[
                    self._row_to_geojson_feature(
                        row=row,
                        vehicle_id=vehicle_id,
                        trip_id=trip_id,
                        enterprise_tz=enterprise_tz,
                    )
                    for row, trip_id in flat_rows
                ],
            )

        return [
            self._row_to_track_point_out(
                row=row,
                vehicle_id=vehicle_id,
                trip_id=trip_id,
                enterprise_tz=enterprise_tz,
            )
            for row, trip_id in flat_rows
        ]

    async def get_grouped_track(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
        format: TrackFormat,
        enterprise_timezone: str | None = None,
    ) -> list[TripTrackGroupModel]:
        enterprise_tz = await self._enterprise_timezone(vehicle_id, enterprise_timezone)

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        trips = await self._trip_repo.get(
            TripFilter(
                vehicle_id=vehicle_id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=None,
                offset=None,
                load_relations=False,
            )
        )

        points_by_trip = await self._get_points_by_trip(vehicle_id, trips)
        result: list[TripTrackGroupModel] = []
        for trip in trips:
            rows = points_by_trip[trip.id]
            result.append(
                TripTrackGroupModel(
                    trip_id=trip.id,
                    vehicle_id=vehicle_id,
                    started_at_utc=trip.started_at_utc,
                    ended_at_utc=trip.ended_at_utc,
                    started_at_enterprise=to_enterprise_tz(
                        trip.started_at_utc,
                        enterprise_tz,
                    ),
                    ended_at_enterprise=to_enterprise_tz(
                        trip.ended_at_utc,
                        enterprise_tz,
                    ),
                    enterprise_timezone=enterprise_tz,
                    points=(
                        [
                            self._row_to_track_point_out(
                                row=row,
                                vehicle_id=vehicle_id,
                                trip_id=trip.id,
                                enterprise_tz=enterprise_tz,
                            )
                            for row in rows
                        ]
                        if format == TrackFormat.json
                        else None
                    ),
                    track=(
                        GeoJSONFeatureCollectionModel(
                            type="FeatureCollection",
                            features=[
                                self._row_to_geojson_feature(
                                    row=row,
                                    vehicle_id=vehicle_id,
                                    trip_id=trip.id,
                                    enterprise_tz=enterprise_tz,
                                )
                                for row in rows
                            ],
                        )
                        if format == TrackFormat.geojson
                        else None
                    ),
                )
            )

        return result

    async def _enterprise_timezone(
        self,
        vehicle_id: int,
        enterprise_timezone: str | None,
    ) -> str:
        if enterprise_timezone is not None:
            return enterprise_timezone

        vehicle = await self._vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found")

        enterprise = vehicle.enterprise
        return enterprise.timezone if enterprise and enterprise.timezone else "UTC"

    async def _get_points_by_trip(self, vehicle_id: int, trips) -> dict[int, list[Any]]:
        points_by_trip: dict[int, list[Any]] = defaultdict(list)
        if not trips:
            return points_by_trip

        rows = await self._track_repo.get(
            VehicleTrackFilter(
                vehicle_id=vehicle_id,
                intervals=[(trip.started_at_utc, trip.ended_at_utc) for trip in trips],
            )
        )

        trip_index = 0
        for row in rows:
            while trip_index < len(trips) and row.recorded_at_utc > trips[trip_index].ended_at_utc:
                trip_index += 1
            if trip_index >= len(trips):
                break
            trip = trips[trip_index]
            if trip.started_at_utc <= row.recorded_at_utc <= trip.ended_at_utc:
                points_by_trip[trip.id].append(row)
        return points_by_trip

    def _row_to_track_point_out(
        self,
        *,
        row: Any,
        vehicle_id: int,
        trip_id: int | None,
        enterprise_tz: str,
    ) -> VehicleTrackPointModel:
        return VehicleTrackPointModel(
            id=row.id,
            trip_id=trip_id,
            recorded_at_utc=row.recorded_at_utc,
            recorded_at_enterprise=to_enterprise_tz(
                row.recorded_at_utc,
                enterprise_tz,
            ),
            latitude=row.latitude,
            longitude=row.longitude,
        )

    def _row_to_geojson_feature(
        self,
        *,
        row: Any,
        vehicle_id: int,
        trip_id: int | None,
        enterprise_tz: str,
    ) -> GeoJSONFeatureModel:
        return GeoJSONFeatureModel(
            type="Feature",
            geometry=GeoJSONGeometryModel(
                type="Point",
                coordinates=[row.longitude, row.latitude],
            ),
            properties={
                "vehicle_id": vehicle_id,
                "trip_id": trip_id,
                "recorded_at_utc": row.recorded_at_utc.isoformat(),
                "recorded_at_enterprise": to_enterprise_tz(
                    row.recorded_at_utc,
                    enterprise_tz,
                ).isoformat(),
                "enterprise_timezone": enterprise_tz,
            },
        )
