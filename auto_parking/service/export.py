import csv
import io
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from auto_parking.core.domain.import_export_format import ExportFormat
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

    async def export_enterprise_vehicles(
        self,
        enterprise_id: int,
        format: ExportFormat = ExportFormat.json,
    ) -> str:
        enterprise = await self._enterprise_repo.get_by_id(enterprise_id)
        if not enterprise:
            raise NotFoundError("Enterprise not found")

        vehicles = await self._vehicle_repo.get_by_enterprise_id(enterprise_id)

        result: dict[str, Any] = {
            "enterprise": {
                "id": enterprise.id,
                "name": enterprise.name,
                "settlement": enterprise.settlement,
                "timezone": enterprise.timezone or "UTC",
            },
            "vehicles": [
                {
                    "id": vehicle.id,
                    "price": vehicle.price,
                    "mileage": vehicle.mileage,
                    "vehicle_number": vehicle.vehicle_number,
                    "owners_count": vehicle.owners_count,
                    "accident_number": vehicle.accident_number,
                    "manufacture_year": vehicle.manufacture_year,
                    "model_id": vehicle.model_id,
                    "enterprise_id": vehicle.enterprise_id,
                    "active_driver_id": vehicle.active_driver_id,
                    "color": vehicle.color,
                    "purchased_at_utc": (
                        vehicle.purchased_at_utc.isoformat() if vehicle.purchased_at_utc else None
                    ),
                }
                for vehicle in vehicles
            ],
        }

        if format == ExportFormat.json:
            return json.dumps(result, ensure_ascii=False, indent=2)

        if format == ExportFormat.csv:
            return self._enterprise_vehicles_to_csv(result)

        raise ValueError("Unsupported export format")

    async def export_vehicle_trips(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
        format: ExportFormat = ExportFormat.json,
    ) -> str:
        vehicle = await self._vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found")

        enterprise = vehicle.enterprise

        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

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

        result: dict[str, Any] = {
            "vehicle": {
                "id": vehicle.id,
                "price": vehicle.price,
                "mileage": vehicle.mileage,
                "vehicle_number": vehicle.vehicle_number,
                "owners_count": vehicle.owners_count,
                "accident_number": vehicle.accident_number,
                "manufacture_year": vehicle.manufacture_year,
                "model_id": vehicle.model_id,
                "enterprise_id": vehicle.enterprise_id,
                "active_driver_id": vehicle.active_driver_id,
                "color": vehicle.color,
                "purchased_at_utc": (
                    vehicle.purchased_at_utc.isoformat() if vehicle.purchased_at_utc else None
                ),
            },
            "enterprise": {
                "id": enterprise.id if enterprise else None,
                "timezone": enterprise.timezone if enterprise else "UTC",
            },
            "export": {
                "date_from_utc": date_from_utc.isoformat(),
                "date_to_utc": date_to_utc.isoformat(),
            },
            "trips": self._build_trip_rows(
                trips=trips,
                points=points,
            ),
        }

        if format == ExportFormat.json:
            return json.dumps(result, ensure_ascii=False, indent=2)

        if format == ExportFormat.csv:
            return self._vehicle_trips_to_csv(result)

        raise ValueError("Unsupported export format")

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
                    "price": vehicle.price,
                    "mileage": vehicle.mileage,
                    "vehicle_number": vehicle.vehicle_number,
                    "owners_count": vehicle.owners_count,
                    "accident_number": vehicle.accident_number,
                    "manufacture_year": vehicle.manufacture_year,
                    "model_id": vehicle.model_id,
                    "enterprise_id": vehicle.enterprise_id,
                    "active_driver_id": vehicle.active_driver_id,
                    "color": vehicle.color,
                    "purchased_at_utc": (
                        vehicle.purchased_at_utc.isoformat() if vehicle.purchased_at_utc else None
                    ),
                    "trips": self._build_trip_rows(
                        trips=trips,
                        points=points,
                    ),
                }
            )

        if format == ExportFormat.json:
            return json.dumps(result, ensure_ascii=False, indent=2)

        if format == ExportFormat.csv:
            return self._enterprise_full_to_csv(result)

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

    def _enterprise_vehicles_to_csv(self, data: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "enterprise_id",
                "enterprise_name",
                "enterprise_settlement",
                "enterprise_timezone",
                "vehicle_id",
                "vehicle_price",
                "vehicle_mileage",
                "vehicle_number",
                "vehicle_owners_count",
                "vehicle_accident_number",
                "vehicle_manufacture_year",
                "vehicle_model_id",
                "vehicle_enterprise_id",
                "vehicle_active_driver_id",
                "vehicle_color",
                "vehicle_purchased_at_utc",
            ]
        )

        enterprise = data["enterprise"]

        for vehicle in data["vehicles"]:
            writer.writerow(
                [
                    enterprise["id"],
                    enterprise["name"],
                    enterprise["settlement"],
                    enterprise["timezone"],
                    vehicle["id"],
                    vehicle["price"],
                    vehicle["mileage"],
                    vehicle["vehicle_number"],
                    vehicle["owners_count"],
                    vehicle["accident_number"],
                    vehicle["manufacture_year"],
                    vehicle["model_id"],
                    vehicle["enterprise_id"],
                    vehicle["active_driver_id"],
                    vehicle["color"],
                    vehicle["purchased_at_utc"],
                ]
            )

        return output.getvalue()

    def _vehicle_trips_to_csv(self, data: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
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

        vehicle = data["vehicle"]

        if not data["trips"]:
            writer.writerow(
                [
                    vehicle["id"],
                    vehicle["vehicle_number"],
                    vehicle["model_id"],
                    vehicle["manufacture_year"],
                    vehicle["color"],
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            return output.getvalue()

        for trip in data["trips"]:
            trip_base = [
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
            ]

            points = trip["points"]

            if not points:
                writer.writerow(
                    trip_base
                    + [
                        "",
                        "",
                        "",
                    ]
                )
                continue

            for point in points:
                writer.writerow(
                    trip_base
                    + [
                        point["recorded_at_utc"],
                        point["latitude"],
                        point["longitude"],
                    ]
                )

        return output.getvalue()

    def _enterprise_full_to_csv(self, data: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "enterprise_id",
                "enterprise_name",
                "enterprise_settlement",
                "enterprise_timezone",
                "vehicle_id",
                "vehicle_price",
                "vehicle_mileage",
                "vehicle_number",
                "vehicle_owners_count",
                "vehicle_accident_number",
                "vehicle_manufacture_year",
                "vehicle_model_id",
                "vehicle_enterprise_id",
                "vehicle_active_driver_id",
                "vehicle_color",
                "vehicle_purchased_at_utc",
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
            vehicle_base = [
                enterprise["id"],
                enterprise["name"],
                enterprise["settlement"],
                enterprise["timezone"],
                vehicle["id"],
                vehicle["price"],
                vehicle["mileage"],
                vehicle["vehicle_number"],
                vehicle["owners_count"],
                vehicle["accident_number"],
                vehicle["manufacture_year"],
                vehicle["model_id"],
                vehicle["enterprise_id"],
                vehicle["active_driver_id"],
                vehicle["color"],
                vehicle["purchased_at_utc"],
            ]

            if not vehicle["trips"]:
                writer.writerow(
                    vehicle_base
                    + [
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
                continue

            for trip in vehicle["trips"]:
                trip_base = [
                    trip["id"],
                    trip["started_at_utc"],
                    trip["ended_at_utc"],
                    trip["start_point_id"],
                    trip["end_point_id"],
                ]

                points = trip["points"]

                if not points:
                    writer.writerow(
                        vehicle_base
                        + trip_base
                        + [
                            "",
                            "",
                            "",
                        ]
                    )
                    continue

                for point in points:
                    writer.writerow(
                        vehicle_base
                        + trip_base
                        + [
                            point["recorded_at_utc"],
                            point["latitude"],
                            point["longitude"],
                        ]
                    )

        return output.getvalue()
