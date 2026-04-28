import csv
import io
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from auto_parking.core.domain.export_format import ExportFormat
from auto_parking.core.errors import NotFoundError
from auto_parking.core.utils.datetime import to_utc
from auto_parking.db.models import Trip
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.trip import TripRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.repo.vehicle_track import VehicleTrackRepository


class ExportService:
    def __init__(
        self,
        enterprise_repo: EnterpriseRepository,
        vehicle_repo: VehicleRepository,
        trip_repo: TripRepository,
        track_repo: VehicleTrackRepository,
    ) -> None:
        self._enterprise_repo = enterprise_repo
        self._vehicle_repo = vehicle_repo
        self._trip_repo = trip_repo
        self._track_repo = track_repo

    async def export_enterprise_full(
        self,
        enterprise_id: int,
        date_from: datetime,
        date_to: datetime,
        format: ExportFormat = ExportFormat.json,
    ) -> str:
        enterprise = await self._enterprise_repo.get_by_id(enterprise_id)
        if not enterprise:
            raise NotFoundError("Enterprise not found")

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        vehicles = await self._vehicle_repo.get_by_enterprise_id(enterprise_id)

        result: dict[str, Any] = {
            "enterprise": {
                "id": enterprise.id,
                "name": enterprise.name,
                "settlement": enterprise.settlement,
                "timezone": enterprise.timezone or "UTC",
            },
            "export": {
                "date_from_utc": date_from_utc.isoformat(),
                "date_to_utc": date_to_utc.isoformat(),
            },
            "vehicles": [],
        }

        for vehicle in vehicles:
            trips = await self._trip_repo.get_trips_inside_range(
                vehicle_id=vehicle.id,
                date_from_utc=date_from_utc,
                date_to_utc=date_to_utc,
            )

            intervals = [(trip.started_at_utc, trip.ended_at_utc) for trip in trips]

            points = await self._track_repo.get_points_by_intervals(
                vehicle_id=vehicle.id,
                intervals=intervals,
            )

            result["vehicles"].append(
                {
                    "id": vehicle.id,
                    "vehicle_number": vehicle.vehicle_number,
                    "model_id": vehicle.model_id,
                    "manufacture_year": vehicle.manufacture_year,
                    "color": vehicle.color,
                    "trips": self._build_trip_rows(
                        trips=trips,
                        points=points,
                    ),
                }
            )

        if format == ExportFormat.json:
            return json.dumps(result, ensure_ascii=False, indent=2)

        if format == ExportFormat.csv:
            return self._to_csv(result)

        raise ValueError("Unsupported export format")

    def _build_trip_rows(
        self,
        *,
        trips: Sequence[Trip],
        points: Sequence[Any],
    ) -> list[dict[str, Any]]:
        trip_rows: list[dict[str, Any]] = [
            {
                "id": trip.id,
                "vehicle_id": trip.vehicle_id,
                "started_at_utc": trip.started_at_utc.isoformat(),
                "ended_at_utc": trip.ended_at_utc.isoformat(),
                "start_point_id": trip.start_point_id,
                "end_point_id": trip.end_point_id,
                "points": [],
            }
            for trip in trips
        ]

        trip_index = 0

        for point in points:
            while (
                trip_index < len(trips) and point.recorded_at_utc > trips[trip_index].ended_at_utc
            ):
                trip_index += 1

            if trip_index >= len(trips):
                break

            trip = trips[trip_index]

            if trip.started_at_utc <= point.recorded_at_utc <= trip.ended_at_utc:
                trip_rows[trip_index]["points"].append(
                    {
                        "recorded_at_utc": point.recorded_at_utc.isoformat(),
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                    }
                )

        return trip_rows

    def _to_csv(self, data: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "enterprise_id",
                "enterprise_name",
                "enterprise_settlement",
                "enterprise_timezone",
                "vehicle_id",
                "vehicle_number",
                "vehicle_model_id",
                "vehicle_manufacture_year",
                "vehicle_color",
                "trip_id",
                "trip_started_at_utc",
                "trip_ended_at_utc",
                "trip_start_point_id",
                "trip_end_point_id",
                "point_recorded_at_utc",
                "point_latitude",
                "point_longitude",
            ]
        )

        enterprise = data["enterprise"]

        for vehicle in data["vehicles"]:
            for trip in vehicle["trips"]:
                points = trip["points"]

                if not points:
                    continue

                for point in points:
                    writer.writerow(
                        [
                            enterprise["id"],
                            enterprise["name"],
                            enterprise["settlement"],
                            enterprise["timezone"],
                            vehicle["id"],
                            vehicle["vehicle_number"],
                            vehicle["model_id"],
                            vehicle["manufacture_year"],
                            vehicle["color"],
                            trip["id"],
                            trip["started_at_utc"],
                            trip["ended_at_utc"],
                            trip["start_point_id"],
                            trip["end_point_id"],
                            point["recorded_at_utc"],
                            point["latitude"],
                            point["longitude"],
                        ]
                    )

        return output.getvalue()
