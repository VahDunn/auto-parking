import json
from datetime import datetime
from time import perf_counter
from typing import TYPE_CHECKING

from auto_parking.core.domain.enums import TrackFormat
from auto_parking.core.domain.models import (
    GeoJSONFeatureCollectionModel,
    GeoJSONFeatureModel,
    GeoJSONGeometryModel,
    VehicleTrackPointModel,
)
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc
from auto_parking.observability.performance import log_cache_lookup
from auto_parking.ports.cache import CacheClient

if TYPE_CHECKING:
    from auto_parking.repo.vehicle_track import VehicleTrackRepository


class VehicleTrackService:
    def __init__(
        self,
        track_repo: "VehicleTrackRepository",
        cache: CacheClient | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._track_repo = track_repo
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def get_track(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
        format: TrackFormat,
        enterprise_timezone: str,
    ) -> list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel:
        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)
        cache_key = self._cache_key(
            vehicle_id,
            date_from_utc,
            date_to_utc,
            format,
            enterprise_timezone,
        )

        cached = await self._get_cached_track(cache_key, format)
        if cached is not None:
            return cached

        rows = await self._track_repo.get_coordinates(
            vehicle_id=vehicle_id,
            date_from_utc=date_from_utc,
            date_to_utc=date_to_utc,
        )
        track = self._build_track(
            rows,
            vehicle_id=vehicle_id,
            format=format,
            enterprise_timezone=enterprise_timezone,
        )
        await self._cache_track(cache_key, track)
        return track

    async def _get_cached_track(
        self,
        key: str,
        format: TrackFormat,
    ) -> list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel | None:
        if self._cache is None:
            return None

        started_at = perf_counter()
        try:
            cached = await self._cache.get_text(key)
            log_cache_lookup(
                operation="vehicle_track_payload",
                result="hit" if cached is not None else "miss",
                duration_seconds=perf_counter() - started_at,
            )
            if cached is None:
                return None
            return self._track_from_cache(cached, format)
        except Exception:
            log_cache_lookup(
                operation="vehicle_track_payload",
                result="error",
                duration_seconds=perf_counter() - started_at,
            )
            return None

    async def _cache_track(
        self,
        key: str,
        track: list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel,
    ) -> None:
        if self._cache is None:
            return

        try:
            await self._cache.set_text(
                key,
                self._track_to_cache(track),
                ttl_seconds=self._cache_ttl_seconds,
            )
        except Exception:
            return None

    @staticmethod
    def _cache_key(
        vehicle_id: int,
        date_from_utc: datetime,
        date_to_utc: datetime,
        format: TrackFormat,
        enterprise_timezone: str,
    ) -> str:
        return (
            f"vehicle-track-domain:{vehicle_id}:{format.value}:{enterprise_timezone}:"
            f"{date_from_utc.isoformat()}:{date_to_utc.isoformat()}"
        )

    @staticmethod
    def _build_track(
        rows,
        *,
        vehicle_id: int,
        format: TrackFormat,
        enterprise_timezone: str,
    ) -> list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel:
        if format == TrackFormat.geojson:
            return GeoJSONFeatureCollectionModel(
                type="FeatureCollection",
                features=[
                    GeoJSONFeatureModel(
                        type="Feature",
                        geometry=GeoJSONGeometryModel(
                            type="Point",
                            coordinates=[row.longitude, row.latitude],
                        ),
                        properties={
                            "vehicle_id": vehicle_id,
                            "recorded_at_utc": row.recorded_at_utc.isoformat(),
                            "recorded_at_enterprise": to_enterprise_tz(
                                row.recorded_at_utc,
                                enterprise_timezone,
                            ).isoformat(),
                            "enterprise_timezone": enterprise_timezone,
                        },
                    )
                    for row in rows
                ],
            )

        return [
            VehicleTrackPointModel(
                id=vehicle_id,
                trip_id=None,
                recorded_at_utc=row.recorded_at_utc,
                recorded_at_enterprise=to_enterprise_tz(
                    row.recorded_at_utc,
                    enterprise_timezone,
                ),
                latitude=row.latitude,
                longitude=row.longitude,
            )
            for row in rows
        ]

    @staticmethod
    def _track_to_cache(
        track: list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel,
    ) -> str:
        if isinstance(track, GeoJSONFeatureCollectionModel):
            return json.dumps(track.to_dict())

        return json.dumps(
            [
                {
                    **point.to_dict(),
                    "recorded_at_utc": point.recorded_at_utc.isoformat(),
                    "recorded_at_enterprise": point.recorded_at_enterprise.isoformat(),
                }
                for point in track
            ]
        )

    @staticmethod
    def _track_from_cache(
        value: str,
        format: TrackFormat,
    ) -> list[VehicleTrackPointModel] | GeoJSONFeatureCollectionModel:
        data = json.loads(value)
        if format == TrackFormat.geojson:
            return GeoJSONFeatureCollectionModel(
                type=data["type"],
                features=[
                    GeoJSONFeatureModel(
                        type=feature["type"],
                        geometry=GeoJSONGeometryModel(
                            type=feature["geometry"]["type"],
                            coordinates=feature["geometry"]["coordinates"],
                        ),
                        properties=feature["properties"],
                    )
                    for feature in data["features"]
                ],
            )

        return [
            VehicleTrackPointModel(
                id=point["id"],
                trip_id=point["trip_id"],
                recorded_at_utc=datetime.fromisoformat(point["recorded_at_utc"]),
                recorded_at_enterprise=datetime.fromisoformat(
                    point["recorded_at_enterprise"]
                ),
                latitude=point["latitude"],
                longitude=point["longitude"],
            )
            for point in data
        ]
