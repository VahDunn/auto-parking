from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from auto_parking.core.domain.models import TripModel
from auto_parking.filter import TripFilter

if TYPE_CHECKING:
    from auto_parking.repo.trip import TripRepository
    from auto_parking.repo.vehicle import VehicleRepository
    from auto_parking.repo.vehicle_track import VehicleTrackRepository
    from auto_parking.service.trip import TripService


@dataclass(frozen=True)
class GpxTrackPoint:
    latitude: float
    longitude: float
    recorded_at_utc: datetime


class GpxImportService:
    def __init__(
        self,
        vehicle_repo: "VehicleRepository",
        trip_repo: "TripRepository",
        track_repo: "VehicleTrackRepository",
        trip_service: "TripService",
    ) -> None:
        self._vehicle_repo = vehicle_repo
        self._trip_repo = trip_repo
        self._track_repo = track_repo
        self._trip_service = trip_service

    async def import_vehicle_trip(
        self,
        *,
        vehicle_id: int,
        raw_gpx: bytes,
    ) -> int:
        vehicle = await self._vehicle_repo.get_by_id(vehicle_id)
        if vehicle is None:
            raise ValueError("Vehicle not found")

        points = self._parse_gpx(raw_gpx)

        if len(points) < 2:
            raise ValueError("GPX track must contain at least 2 points with time")

        started_at_utc = points[0].recorded_at_utc
        ended_at_utc = points[-1].recorded_at_utc

        if ended_at_utc < started_at_utc:
            raise ValueError("GPX track time range is invalid")

        candidate_trips = await self._trip_repo.get(
            TripFilter(
                vehicle_id=vehicle_id,
                started_to=ended_at_utc,
                limit=None,
                offset=None,
            )
        )

        overlapping = [
            trip
            for trip in candidate_trips
            if self._trip_overlaps(
                trip_started_at_utc=trip.started_at_utc,
                trip_ended_at_utc=trip.ended_at_utc,
                started_at_utc=started_at_utc,
                ended_at_utc=ended_at_utc,
            )
        ]

        if overlapping:
            raise ValueError("GPX не может перекрывать существующие поездки")

        existing_points = await self._track_repo.get_points_by_intervals(
            vehicle_id=vehicle_id,
            intervals=[(started_at_utc, ended_at_utc)],
        )

        point_ids_by_key = {
            self._point_key(
                latitude=row.latitude,
                longitude=row.longitude,
                recorded_at_utc=row.recorded_at_utc,
            ): row.id
            for row in existing_points
        }

        missing_points = [
            point
            for point in points
            if self._point_key(
                latitude=point.latitude,
                longitude=point.longitude,
                recorded_at_utc=point.recorded_at_utc,
            )
            not in point_ids_by_key
        ]

        created_points = await self._track_repo.create_points_bulk(
            [
                {
                    "vehicle_id": vehicle_id,
                    "recorded_at_utc": point.recorded_at_utc,
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                }
                for point in missing_points
            ]
        )

        for point, created_point in zip(
            missing_points,
            created_points,
            strict=True,
        ):
            point_ids_by_key[
                self._point_key(
                    latitude=point.latitude,
                    longitude=point.longitude,
                    recorded_at_utc=point.recorded_at_utc,
                )
            ] = created_point.id

        start_point_id = point_ids_by_key[
            self._point_key(
                latitude=points[0].latitude,
                longitude=points[0].longitude,
                recorded_at_utc=points[0].recorded_at_utc,
            )
        ]

        end_point_id = point_ids_by_key[
            self._point_key(
                latitude=points[-1].latitude,
                longitude=points[-1].longitude,
                recorded_at_utc=points[-1].recorded_at_utc,
            )
        ]

        trip = await self._trip_service.create(
            TripModel(
                id=None,
                vehicle_id=vehicle_id,
                started_at_utc=started_at_utc,
                ended_at_utc=ended_at_utc,
                start_point_id=start_point_id,
                end_point_id=end_point_id,
            ),
            include_addresses=False,
        )
        return trip.id

    def _parse_gpx(self, raw_gpx: bytes) -> list[GpxTrackPoint]:
        try:
            root = ElementTree.fromstring(raw_gpx)
        except ElementTree.ParseError as err:
            raise ValueError("Invalid GPX XML") from err

        points: list[GpxTrackPoint] = []

        for element in root.iter():
            if self._local_name(element.tag) != "trkpt":
                continue

            raw_lat = element.attrib.get("lat")
            raw_lon = element.attrib.get("lon")

            if raw_lat is None or raw_lon is None:
                continue

            time_text = self._find_child_text(element, "time")
            if not time_text:
                continue

            try:
                point = GpxTrackPoint(
                    latitude=float(raw_lat),
                    longitude=float(raw_lon),
                    recorded_at_utc=self._parse_gpx_time(time_text),
                )
            except ValueError:
                continue

            points.append(point)

        points.sort(key=lambda item: item.recorded_at_utc)

        unique_points: list[GpxTrackPoint] = []
        seen: set[tuple[datetime, float, float]] = set()

        for point in points:
            key = self._point_key(
                latitude=point.latitude,
                longitude=point.longitude,
                recorded_at_utc=point.recorded_at_utc,
            )

            if key in seen:
                continue

            seen.add(key)
            unique_points.append(point)

        return unique_points

    @staticmethod
    def _point_key(
        *,
        latitude: float,
        longitude: float,
        recorded_at_utc: datetime,
    ) -> tuple[datetime, float, float]:
        return (
            recorded_at_utc,
            round(latitude, 7),
            round(longitude, 7),
        )

    @staticmethod
    def _trip_overlaps(
        *,
        trip_started_at_utc: datetime,
        trip_ended_at_utc: datetime,
        started_at_utc: datetime,
        ended_at_utc: datetime,
    ) -> bool:
        return trip_started_at_utc <= ended_at_utc and trip_ended_at_utc >= started_at_utc

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _find_child_text(
        self,
        element: ElementTree.Element,
        child_name: str,
    ) -> "str | None":
        for child in element:
            if self._local_name(child.tag) == child_name:
                return child.text.strip() if child.text else None

        return None

    @staticmethod
    def _parse_gpx_time(value: str) -> datetime:
        normalized = value.strip()

        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        parsed = datetime.fromisoformat(normalized)

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("GPX point time must be timezone-aware")

        return parsed.astimezone(UTC)
