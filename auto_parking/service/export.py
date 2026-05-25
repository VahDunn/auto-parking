import csv
import io
import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, TypedDict

from auto_parking.core.enums.import_export_format import ExportFormat
from auto_parking.core.errors import NotFoundError
from auto_parking.core.utils.datetime import to_utc
from auto_parking.db.models import Driver, Trip, Vehicle
from auto_parking.filter import DriverFilter, TripFilter, VehicleFilter
from auto_parking.repo.driver import DriverRepository
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.trip import TripRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.repo.vehicle_track import VehicleTrackRepository


class TripEdge(TypedDict):
    start: str | None
    end: str | None


class ExportService:
    def __init__(
        self,
        enterprise_repo: EnterpriseRepository,
        vehicle_repo: VehicleRepository,
        driver_repo: DriverRepository,
        trip_repo: TripRepository,
        track_repo: VehicleTrackRepository,
    ) -> None:
        self._enterprise_repo = enterprise_repo
        self._vehicle_repo = vehicle_repo
        self._driver_repo = driver_repo
        self._trip_repo = trip_repo
        self._track_repo = track_repo

    async def export_enterprise_guid_dump(
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

        enterprise_external_id = self._new_external_id()

        vehicles = await self._vehicle_repo.get(
            VehicleFilter(enterprise_ids=[enterprise_id], limit=None, offset=None)
        )
        drivers = await self._driver_repo.get(
            DriverFilter(id=None, enterprise_ids=[enterprise_id], vehicle_id=None)
        )

        vehicle_external_ids = {vehicle.id: self._new_external_id() for vehicle in vehicles}
        driver_external_ids = {driver.id: self._new_external_id() for driver in drivers}

        result: dict[str, Any] = {
            "dump_format": "auto_parking_guid_export",
            "dump_version": 1,
            "export": {
                "date_from_utc": date_from_utc.isoformat(),
                "date_to_utc": date_to_utc.isoformat(),
            },
            "enterprise": {
                "external_id": enterprise_external_id,
                "source_id": enterprise.id,
                "name": enterprise.name,
                "settlement": enterprise.settlement,
                "timezone": enterprise.timezone or "UTC",
            },
            "drivers": self._build_guid_driver_rows(
                drivers=drivers,
                enterprise_external_id=enterprise_external_id,
                driver_external_ids=driver_external_ids,
                vehicle_external_ids=vehicle_external_ids,
            ),
            "vehicles": self._build_guid_vehicle_rows(
                vehicles=vehicles,
                enterprise_external_id=enterprise_external_id,
                vehicle_external_ids=vehicle_external_ids,
                driver_external_ids=driver_external_ids,
            ),
            "vehicle_driver_assignments": self._build_guid_assignment_rows(
                drivers=drivers,
                driver_external_ids=driver_external_ids,
                vehicle_external_ids=vehicle_external_ids,
            ),
            "trips": [],
            "points": [],
        }

        for vehicle in vehicles:
            trips = await self._trip_repo.get(
                TripFilter(
                    vehicle_id=vehicle.id,
                    started_from=date_from_utc,
                    ended_to=date_to_utc,
                    limit=None,
                    offset=None,
                )
            )

            trip_external_ids = {trip.id: self._new_external_id() for trip in trips}
            intervals = [(trip.started_at_utc, trip.ended_at_utc) for trip in trips]

            points = await self._track_repo.get_points_by_intervals(
                vehicle_id=vehicle.id,
                intervals=intervals,
            )

            point_rows, trip_edges = self._build_guid_point_rows(
                trips=trips,
                points=points,
                vehicle_external_id=vehicle_external_ids[vehicle.id],
                trip_external_ids=trip_external_ids,
            )

            result["trips"].extend(
                self._build_guid_trip_rows(
                    trips=trips,
                    vehicle_external_id=vehicle_external_ids[vehicle.id],
                    trip_external_ids=trip_external_ids,
                    trip_edges=trip_edges,
                )
            )

            result["points"].extend(point_rows)

        if format == ExportFormat.json:
            return json.dumps(result, ensure_ascii=False, indent=2)

        if format == ExportFormat.csv:
            return self._guid_dump_to_csv(result)

        raise ValueError("Unsupported export format")

    async def export_enterprise_vehicles(
        self,
        enterprise_id: int,
        format: ExportFormat = ExportFormat.json,
    ) -> str:
        enterprise = await self._enterprise_repo.get_by_id(enterprise_id)
        if not enterprise:
            raise NotFoundError("Enterprise not found")

        vehicles = await self._vehicle_repo.get(
            VehicleFilter(enterprise_ids=[enterprise_id], limit=None, offset=None)
        )

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

        trips = await self._trip_repo.get(
            TripFilter(
                vehicle_id=vehicle.id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=None,
                offset=None,
            )
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
            "trips": self._build_trip_rows(trips=trips, points=points),
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

        vehicles = await self._vehicle_repo.get(
            VehicleFilter(enterprise_ids=[enterprise_id], limit=None, offset=None)
        )

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
            "vehicle_driver_assignments": self._build_assignment_rows(vehicles),
        }

        for vehicle in vehicles:
            trips = await self._trip_repo.get(
                TripFilter(
                    vehicle_id=vehicle.id,
                    started_from=date_from_utc,
                    ended_to=date_to_utc,
                    limit=None,
                    offset=None,
                )
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
                    "trips": self._build_trip_rows(trips=trips, points=points),
                }
            )

        if format == ExportFormat.json:
            return json.dumps(result, ensure_ascii=False, indent=2)

        if format == ExportFormat.csv:
            return self._enterprise_full_to_csv(result)

        raise ValueError("Unsupported export format")

    def _build_assignment_rows(
        self,
        vehicles: Sequence[Vehicle],
    ) -> list[dict[str, int]]:
        rows: list[dict[str, int]] = []
        seen: set[tuple[int, int]] = set()

        for vehicle in vehicles:
            for driver in vehicle.drivers:
                key = (vehicle.id, driver.id)

                if key in seen:
                    continue

                seen.add(key)

                rows.append(
                    {
                        "vehicle_id": vehicle.id,
                        "driver_id": driver.id,
                    }
                )

        return rows

    def _build_guid_driver_rows(
        self,
        *,
        drivers: Sequence[Driver],
        enterprise_external_id: str,
        driver_external_ids: dict[int, str],
        vehicle_external_ids: dict[int, str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for driver in drivers:
            active_vehicle_id = getattr(driver, "active_vehicle_id", None)

            active_vehicle_external_id = (
                vehicle_external_ids.get(active_vehicle_id)
                if isinstance(active_vehicle_id, int)
                else None
            )

            rows.append(
                {
                    "external_id": driver_external_ids[driver.id],
                    "source_id": driver.id,
                    "enterprise_external_id": enterprise_external_id,
                    "name": driver.name,
                    "salary_rub": getattr(driver, "salary_rub", None),
                    "active_vehicle_external_id": active_vehicle_external_id,
                }
            )

        return rows

    def _build_guid_vehicle_rows(
        self,
        *,
        vehicles: Sequence[Vehicle],
        enterprise_external_id: str,
        vehicle_external_ids: dict[int, str],
        driver_external_ids: dict[int, str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for vehicle in vehicles:
            active_driver_external_id = (
                driver_external_ids.get(vehicle.active_driver_id)
                if vehicle.active_driver_id is not None
                else None
            )

            rows.append(
                {
                    "external_id": vehicle_external_ids[vehicle.id],
                    "source_id": vehicle.id,
                    "enterprise_external_id": enterprise_external_id,
                    "price": vehicle.price,
                    "mileage": vehicle.mileage,
                    "vehicle_number": vehicle.vehicle_number,
                    "owners_count": vehicle.owners_count,
                    "accident_number": vehicle.accident_number,
                    "manufacture_year": vehicle.manufacture_year,
                    "model_id": vehicle.model_id,
                    "active_driver_external_id": active_driver_external_id,
                    "color": vehicle.color,
                    "purchased_at_utc": (
                        vehicle.purchased_at_utc.isoformat() if vehicle.purchased_at_utc else None
                    ),
                }
            )

        return rows

    def _build_guid_assignment_rows(
        self,
        *,
        drivers: Sequence[Driver],
        driver_external_ids: dict[int, str],
        vehicle_external_ids: dict[int, str],
    ) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for driver in drivers:
            driver_external_id = driver_external_ids[driver.id]

            for vehicle in driver.vehicles:
                vehicle_external_id = vehicle_external_ids.get(vehicle.id)
                if vehicle_external_id is None:
                    continue

                key = (driver_external_id, vehicle_external_id)
                if key in seen:
                    continue

                seen.add(key)

                rows.append(
                    {
                        "driver_external_id": driver_external_id,
                        "vehicle_external_id": vehicle_external_id,
                    }
                )

        return rows

    def _build_guid_trip_rows(
        self,
        *,
        trips: Sequence[Trip],
        vehicle_external_id: str,
        trip_external_ids: dict[int, str],
        trip_edges: dict[int, TripEdge],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for trip in trips:
            edge = trip_edges[trip.id]

            rows.append(
                {
                    "external_id": trip_external_ids[trip.id],
                    "source_id": trip.id,
                    "vehicle_external_id": vehicle_external_id,
                    "started_at_utc": trip.started_at_utc.isoformat(),
                    "ended_at_utc": trip.ended_at_utc.isoformat(),
                    "start_point_external_id": edge["start"],
                    "end_point_external_id": edge["end"],
                }
            )

        return rows

    def _build_guid_point_rows(
        self,
        *,
        trips: Sequence[Trip],
        points: Sequence[Any],
        vehicle_external_id: str,
        trip_external_ids: dict[int, str],
    ) -> tuple[list[dict[str, Any]], dict[int, TripEdge]]:
        rows: list[dict[str, Any]] = []

        trip_edges: dict[int, TripEdge] = {trip.id: {"start": None, "end": None} for trip in trips}

        trip_index = 0

        for point in points:
            while (
                trip_index < len(trips) and point.recorded_at_utc > trips[trip_index].ended_at_utc
            ):
                trip_index += 1

            if trip_index >= len(trips):
                break

            trip = trips[trip_index]

            if not (trip.started_at_utc <= point.recorded_at_utc <= trip.ended_at_utc):
                continue

            point_external_id = self._new_external_id()

            if trip_edges[trip.id]["start"] is None:
                trip_edges[trip.id]["start"] = point_external_id

            trip_edges[trip.id]["end"] = point_external_id

            rows.append(
                {
                    "external_id": point_external_id,
                    "trip_external_id": trip_external_ids[trip.id],
                    "vehicle_external_id": vehicle_external_id,
                    "recorded_at_utc": point.recorded_at_utc.isoformat(),
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                }
            )

        return rows, trip_edges

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
                writer.writerow(trip_base + ["", "", ""])
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
                "row_type",
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
                "assignment_vehicle_id",
                "assignment_driver_id",
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
                "vehicle",
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
                "",
                "",
            ]

            if not vehicle["trips"]:
                writer.writerow(vehicle_base + ["", "", "", "", "", "", "", ""])
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
                    writer.writerow(vehicle_base + trip_base + ["", "", ""])
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

        for assignment in data.get("vehicle_driver_assignments", []):
            writer.writerow(
                [
                    "vehicle_driver_assignment",
                    enterprise["id"],
                    enterprise["name"],
                    enterprise["settlement"],
                    enterprise["timezone"],
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    assignment["vehicle_id"],
                    assignment["driver_id"],
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

    def _guid_dump_to_csv(self, data: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "row_type",
                "external_id",
                "source_id",
                "parent_external_id",
                "related_external_id",
                "payload_json",
            ]
        )

        enterprise = data["enterprise"]

        writer.writerow(
            [
                "enterprise",
                enterprise["external_id"],
                enterprise["source_id"],
                "",
                "",
                json.dumps(enterprise, ensure_ascii=False),
            ]
        )

        for driver in data["drivers"]:
            writer.writerow(
                [
                    "driver",
                    driver["external_id"],
                    driver["source_id"],
                    driver["enterprise_external_id"],
                    driver["active_vehicle_external_id"] or "",
                    json.dumps(driver, ensure_ascii=False),
                ]
            )

        for vehicle in data["vehicles"]:
            writer.writerow(
                [
                    "vehicle",
                    vehicle["external_id"],
                    vehicle["source_id"],
                    vehicle["enterprise_external_id"],
                    vehicle["active_driver_external_id"] or "",
                    json.dumps(vehicle, ensure_ascii=False),
                ]
            )

        for assignment in data["vehicle_driver_assignments"]:
            writer.writerow(
                [
                    "vehicle_driver_assignment",
                    "",
                    "",
                    assignment["driver_external_id"],
                    assignment["vehicle_external_id"],
                    json.dumps(assignment, ensure_ascii=False),
                ]
            )

        for trip in data["trips"]:
            writer.writerow(
                [
                    "trip",
                    trip["external_id"],
                    trip["source_id"],
                    trip["vehicle_external_id"],
                    "",
                    json.dumps(trip, ensure_ascii=False),
                ]
            )

        for point in data["points"]:
            writer.writerow(
                [
                    "point",
                    point["external_id"],
                    "",
                    point["trip_external_id"],
                    point["vehicle_external_id"],
                    json.dumps(point, ensure_ascii=False),
                ]
            )

        return output.getvalue()

    def _new_external_id(self) -> str:
        return str(uuid.uuid4())
