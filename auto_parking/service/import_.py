import csv
import io
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.trip import TripRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.repo.vehicle_track import VehicleTrackRepository


class ImportService:
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

    async def import_enterprise_json(self, raw: bytes) -> dict[str, Any]:
        payload = json.loads(raw.decode("utf-8"))

        enterprise_data = payload["enterprise"]

        enterprise = await self._enterprise_repo.create(
            {
                "name": enterprise_data["name"],
                "settlement": enterprise_data.get("settlement"),
                "timezone": enterprise_data.get("timezone") or "UTC",
            }
        )

        imported_vehicles = 0
        imported_trips = 0
        imported_points = 0

        for vehicle_data in payload.get("vehicles", []):
            vehicle = await self._vehicle_repo.create(
                {
                    "price": vehicle_data.get("price") or 0,
                    "mileage": vehicle_data.get("mileage") or 0,
                    "vehicle_number": vehicle_data["vehicle_number"],
                    "owners_count": vehicle_data.get("owners_count") or 1,
                    "accident_number": vehicle_data.get("accident_number") or 0,
                    "manufacture_year": vehicle_data["manufacture_year"],
                    "model_id": vehicle_data["model_id"],
                    "enterprise_id": enterprise.id,
                    "active_driver_id": None,
                    "color": vehicle_data.get("color"),
                    "purchased_at_utc": self._parse_dt_or_none(
                        vehicle_data.get("purchased_at_utc")
                    ),
                }
            )

            imported_vehicles += 1

            for trip_data in vehicle_data.get("trips", []):
                created_points = []

                for point_data in trip_data.get("points", []):
                    point = await self._track_repo.create_point(
                        vehicle_id=vehicle.id,
                        recorded_at_utc=self._parse_dt(point_data["recorded_at_utc"]),
                        latitude=float(point_data["latitude"]),
                        longitude=float(point_data["longitude"]),
                    )
                    created_points.append(point)
                    imported_points += 1

                if not created_points:
                    continue

                await self._trip_repo.create(
                    {
                        "vehicle_id": vehicle.id,
                        "started_at_utc": self._parse_dt(trip_data["started_at_utc"]),
                        "ended_at_utc": self._parse_dt(trip_data["ended_at_utc"]),
                        "start_point_id": created_points[0].id,
                        "end_point_id": created_points[-1].id,
                    }
                )

                imported_trips += 1

        return {
            "enterprise_id": enterprise.id,
            "imported_vehicles": imported_vehicles,
            "imported_trips": imported_trips,
            "imported_points": imported_points,
        }

    async def import_enterprise_csv(self, raw: bytes) -> dict[str, Any]:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            raise ValueError("CSV is empty")

        first = rows[0]

        enterprise = await self._enterprise_repo.create(
            {
                "name": first["enterprise_name"],
                "settlement": first.get("enterprise_settlement"),
                "timezone": first.get("enterprise_timezone") or "UTC",
            }
        )

        vehicles_by_source_id: dict[str, Any] = {}
        rows_by_vehicle_trip: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

        for row in rows:
            source_vehicle_id = row["vehicle_id"]

            if source_vehicle_id not in vehicles_by_source_id:
                vehicle = await self._vehicle_repo.create(
                    {
                        "price": int(row.get("vehicle_price") or 0),
                        "mileage": int(row.get("vehicle_mileage") or 0),
                        "vehicle_number": row["vehicle_number"],
                        "owners_count": int(row.get("vehicle_owners_count") or 1),
                        "accident_number": int(row.get("vehicle_accident_number") or 0),
                        "manufacture_year": int(row["vehicle_manufacture_year"]),
                        "model_id": int(row["vehicle_model_id"]),
                        "enterprise_id": enterprise.id,
                        "active_driver_id": None,
                        "color": row.get("vehicle_color") or None,
                        "purchased_at_utc": self._parse_dt_or_none(
                            row.get("vehicle_purchased_at_utc")
                        ),
                    }
                )
                vehicles_by_source_id[source_vehicle_id] = vehicle

            source_trip_id = row.get("trip_id") or ""
            if source_trip_id:
                rows_by_vehicle_trip[(source_vehicle_id, source_trip_id)].append(row)

        imported_trips = 0
        imported_points = 0

        for (source_vehicle_id, _source_trip_id), trip_rows in rows_by_vehicle_trip.items():
            vehicle = vehicles_by_source_id[source_vehicle_id]
            created_points = []

            for row in trip_rows:
                if not row.get("point_recorded_at_utc"):
                    continue

                point = await self._track_repo.create_point(
                    vehicle_id=vehicle.id,
                    recorded_at_utc=self._parse_dt(row["point_recorded_at_utc"]),
                    latitude=float(row["point_latitude"]),
                    longitude=float(row["point_longitude"]),
                )
                created_points.append(point)
                imported_points += 1

            if not created_points:
                continue

            first_row = trip_rows[0]

            await self._trip_repo.create(
                {
                    "vehicle_id": vehicle.id,
                    "started_at_utc": self._parse_dt(first_row["trip_started_at_utc"]),
                    "ended_at_utc": self._parse_dt(first_row["trip_ended_at_utc"]),
                    "start_point_id": created_points[0].id,
                    "end_point_id": created_points[-1].id,
                }
            )

            imported_trips += 1

        return {
            "enterprise_id": enterprise.id,
            "imported_vehicles": len(vehicles_by_source_id),
            "imported_trips": imported_trips,
            "imported_points": imported_points,
        }

    def _parse_dt(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _parse_dt_or_none(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return self._parse_dt(value)
