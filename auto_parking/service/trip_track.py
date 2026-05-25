import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from auto_parking.api.schemas.trip_track import TripTrackGroupOut
from auto_parking.api.schemas.vehicle_track import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    TrackFormat,
    VehicleTrackPointOut,
)
from auto_parking.core.errors import NotFoundError
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc
from auto_parking.filter import TripFilter

if TYPE_CHECKING:
    from auto_parking.repo.trip import TripRepository
    from auto_parking.repo.vehicle import VehicleRepository
    from auto_parking.repo.vehicle_track import VehicleTrackRepository


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
    ) -> list[VehicleTrackPointOut] | GeoJSONFeatureCollection:
        vehicle = await self._vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found")

        enterprise = vehicle.enterprise
        enterprise_tz = enterprise.timezone if enterprise and enterprise.timezone else "UTC"

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        trips = await self._trip_repo.get(
            TripFilter(
                vehicle_id=vehicle_id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=None,
                offset=None,
            )
        )

        flat_rows: list[tuple[Any, int]] = []

        for trip in trips:
            rows = await self._track_repo.get_points(
                vehicle_id=vehicle_id,
                date_from_utc=trip.started_at_utc,
                date_to_utc=trip.ended_at_utc,
            )
            flat_rows.extend((row, trip.id) for row in rows)

        flat_rows.sort(key=lambda item: item[0].recorded_at_utc)

        if format == TrackFormat.geojson:
            return GeoJSONFeatureCollection(
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
    ) -> list[TripTrackGroupOut] | list[dict[str, Any]]:
        vehicle = await self._vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found")

        enterprise = vehicle.enterprise
        enterprise_tz = enterprise.timezone if enterprise and enterprise.timezone else "UTC"

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        trips = await self._trip_repo.get(
            TripFilter(
                vehicle_id=vehicle_id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=None,
                offset=None,
            )
        )

        if format == TrackFormat.geojson:
            result_geojson: list[dict[str, Any]] = []

            for trip in trips:
                rows = await self._track_repo.get_points(
                    vehicle_id=vehicle_id,
                    date_from_utc=trip.started_at_utc,
                    date_to_utc=trip.ended_at_utc,
                )
                rows = sorted(rows, key=lambda row: row.recorded_at_utc)

                result_geojson.append(
                    {
                        "trip_id": trip.id,
                        "vehicle_id": vehicle_id,
                        "started_at_utc": trip.started_at_utc.isoformat(),
                        "ended_at_utc": trip.ended_at_utc.isoformat(),
                        "started_at_enterprise": to_enterprise_tz(
                            trip.started_at_utc,
                            enterprise_tz,
                        ).isoformat(),
                        "ended_at_enterprise": to_enterprise_tz(
                            trip.ended_at_utc,
                            enterprise_tz,
                        ).isoformat(),
                        "enterprise_timezone": enterprise_tz,
                        "track": {
                            "type": "FeatureCollection",
                            "features": [
                                self._row_to_geojson_feature(
                                    row=row,
                                    vehicle_id=vehicle_id,
                                    trip_id=trip.id,
                                    enterprise_tz=enterprise_tz,
                                )
                                for row in rows
                            ],
                        },
                    }
                )

            return result_geojson

        result_json: list[TripTrackGroupOut] = []

        for trip in trips:
            rows = await self._track_repo.get_points(
                vehicle_id=vehicle_id,
                date_from_utc=trip.started_at_utc,
                date_to_utc=trip.ended_at_utc,
            )
            rows = sorted(rows, key=lambda row: row.recorded_at_utc)

            points = [
                self._row_to_track_point_out(
                    row=row,
                    vehicle_id=vehicle_id,
                    trip_id=trip.id,
                    enterprise_tz=enterprise_tz,
                )
                for row in rows
            ]

            result_json.append(
                TripTrackGroupOut(
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
                    points=points,
                )
            )

        return result_json

    def _row_to_track_point_out(
        self,
        *,
        row: Any,
        vehicle_id: int,
        trip_id: int | None,
        enterprise_tz: str,
    ) -> VehicleTrackPointOut:
        return VehicleTrackPointOut(
            id=vehicle_id,
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
    ) -> GeoJSONFeature:
        raw_geometry = json.loads(row.geojson)

        return GeoJSONFeature(
            type="Feature",
            geometry=GeoJSONGeometry(
                type=raw_geometry["type"],
                coordinates=raw_geometry["coordinates"],
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
