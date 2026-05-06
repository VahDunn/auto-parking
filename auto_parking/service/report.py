from collections import defaultdict
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Any

from geoalchemy2.shape import to_shape
from shapely import Point

from auto_parking.api.schemas.report import ReportCreate, ReportInfo
from auto_parking.api.schemas.trip import TripFilter
from auto_parking.core.domain.report_period import ReportPeriod
from auto_parking.core.domain.report_type import ReportType
from auto_parking.core.utils.datetime import to_utc
from auto_parking.db.models import Report
from auto_parking.repo.report import ReportRepository
from auto_parking.repo.trip import TripRepository
from auto_parking.repo.vehicle import VehicleRepository


class ReportService:
    def __init__(
        self,
        report_repo: ReportRepository,
        trip_repo: TripRepository,
        vehicle_repo: VehicleRepository,
    ) -> None:
        self._report_repo = report_repo
        self._trip_repo = trip_repo
        self._vehicle_repo = vehicle_repo

    async def get_available_reports(self) -> list[ReportInfo]:
        return [
            ReportInfo(
                type=ReportType.vehicle_mileage,
                title="Пробег автомобиля за период",
                description="Считает пробег автомобиля по поездкам и группирует по дням, месяцам или годам.",
                parameters=["enterprise_id", "vehicle_id", "period", "date_from", "date_to"],
            ),
            ReportInfo(
                type=ReportType.vehicle_activity,
                title="Активность автомобиля",
                description="Считает время движения и простоя автомобиля за период.",
                parameters=["enterprise_id", "vehicle_id", "period", "date_from", "date_to"],
            ),
            ReportInfo(
                type=ReportType.vehicle_geography,
                title="География поездок автомобиля",
                description="Показывает распределение поездок по географическим зонам.",
                parameters=["enterprise_id", "vehicle_id", "date_from", "date_to"],
            ),
        ]

    async def get_all(self, enterprise_ids: set[int] | None = None):
        return await self._report_repo.get_all(enterprise_ids)

    async def get_by_id(self, report_id: int) -> Report | None:
        return await self._report_repo.get_by_id(report_id)

    async def create(self, payload: ReportCreate) -> Report:
        result_json = await self._build_result(payload)

        return await self._report_repo.create(
            {
                "name": payload.name,
                "report_type": payload.report_type,
                "period": payload.period,
                "date_from": payload.date_from,
                "date_to": payload.date_to,
                "enterprise_id": payload.enterprise_id,
                "vehicle_id": payload.vehicle_id,
                "params_json": payload.params_json,
                "result_json": result_json,
            }
        )

    async def rebuild(self, report_id: int) -> Report | None:
        report = await self._report_repo.get_by_id(report_id)
        if report is None:
            return None

        payload = ReportCreate(
            name=report.name,
            report_type=report.report_type,
            period=report.period,
            date_from=report.date_from,
            date_to=report.date_to,
            enterprise_id=report.enterprise_id,
            vehicle_id=report.vehicle_id,
            params_json=report.params_json,
        )

        result_json = await self._build_result(payload)
        return await self._report_repo.update_result(report_id, result_json)

    async def delete(self, report_id: int) -> bool:
        return await self._report_repo.delete(report_id)

    async def _build_result(self, payload: ReportCreate) -> list[dict[str, Any]]:
        if payload.vehicle_id is None:
            raise ValueError("vehicle_id is required for this report type")

        vehicle = await self._vehicle_repo.get_by_id(payload.vehicle_id)
        if vehicle is None:
            raise ValueError("Vehicle not found")

        if vehicle.enterprise_id != payload.enterprise_id:
            raise ValueError("Vehicle does not belong to enterprise")

        if payload.report_type == ReportType.vehicle_mileage:
            return await self._build_vehicle_mileage(payload)

        if payload.report_type == ReportType.vehicle_activity:
            return await self._build_vehicle_activity(payload)

        if payload.report_type == ReportType.vehicle_geography:
            return await self._build_vehicle_geography(payload)

        raise ValueError("Unsupported report type")

    async def _get_trips(self, payload: ReportCreate):
        date_from_utc = to_utc(payload.date_from)
        date_to_utc = to_utc(payload.date_to)

        return await self._trip_repo.get(
            TripFilter(
                vehicle_id=payload.vehicle_id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=1000,
                sort_by="started_at_utc",
            )
        )

    async def _build_vehicle_mileage(self, payload: ReportCreate) -> list[dict[str, Any]]:
        grouped: dict[str, float] = defaultdict(float)

        for trip in await self._get_trips(payload):
            distance_km = self._trip_distance_km(trip)
            grouped[self._period_key(trip.started_at_utc, payload.period)] += distance_km

        return [
            {
                "time": key,
                "value": round(value, 3),
                "extra": {"unit": "km"},
            }
            for key, value in sorted(grouped.items())
        ]

    async def _build_vehicle_activity(self, payload: ReportCreate) -> list[dict[str, Any]]:
        trips = await self._get_trips(payload)

        moving_by_period: dict[str, float] = defaultdict(float)

        for trip in trips:
            key = self._period_key(trip.started_at_utc, payload.period)
            duration_hours = (trip.ended_at_utc - trip.started_at_utc).total_seconds() / 3600
            moving_by_period[key] += duration_hours

        result = []

        for key, period_hours in self._period_total_hours(
            payload.date_from,
            payload.date_to,
            payload.period,
        ).items():
            moving_hours = moving_by_period.get(key, 0.0)
            idle_hours = max(period_hours - moving_hours, 0.0)

            result.append(
                {
                    "time": key,
                    "value": round(moving_hours, 3),
                    "extra": {
                        "moving_hours": round(moving_hours, 3),
                        "idle_hours": round(idle_hours, 3),
                        "unit": "hours",
                    },
                }
            )

        return result

    async def _build_vehicle_geography(self, payload: ReportCreate) -> list[dict[str, Any]]:
        trips = await self._get_trips(payload)

        zones: dict[tuple[str, str], int] = defaultdict(int)

        for trip in trips:
            if trip.start_point is None:
                continue

            lat, lon = self._point_lat_lon(trip.start_point)
            precision = int(payload.params_json.get("precision", 2))

            time_key = self._period_key(trip.started_at_utc, payload.period)
            zone = f"{round(lat, precision)}_{round(lon, precision)}"

            zones[(time_key, zone)] += 1

        return [
            {
                "time": time_key,
                "value": count,
                "extra": {
                    "unit": "trip_count",
                    "zone": zone,
                },
            }
            for (time_key, zone), count in sorted(zones.items())
        ]

    def _trip_distance_km(self, trip) -> float:
        if trip.start_point is None or trip.end_point is None:
            return 0.0

        start_lat, start_lon = self._point_lat_lon(trip.start_point)
        end_lat, end_lon = self._point_lat_lon(trip.end_point)

        return self._haversine_km(start_lat, start_lon, end_lat, end_lon)

    @staticmethod
    def _period_key(value: datetime, period: ReportPeriod) -> str:
        if period == ReportPeriod.day:
            return value.strftime("%Y-%m-%d")
        if period == ReportPeriod.month:
            return value.strftime("%Y-%m")
        return value.strftime("%Y")

    @staticmethod
    def _period_total_hours(
        date_from: datetime,
        date_to: datetime,
        period: ReportPeriod,
    ) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)

        cursor = date_from
        while cursor < date_to:
            if period == ReportPeriod.day:
                next_cursor = datetime(
                    cursor.year,
                    cursor.month,
                    cursor.day,
                    tzinfo=cursor.tzinfo,
                ) + timedelta(days=1)
            elif period == ReportPeriod.month:
                if cursor.month == 12:
                    next_cursor = datetime(cursor.year + 1, 1, 1, tzinfo=cursor.tzinfo)
                else:
                    next_cursor = datetime(cursor.year, cursor.month + 1, 1, tzinfo=cursor.tzinfo)
            else:
                next_cursor = datetime(cursor.year + 1, 1, 1, tzinfo=cursor.tzinfo)

            chunk_end = min(next_cursor, date_to)
            key = ReportService._period_key(cursor, period)
            result[key] += (chunk_end - cursor).total_seconds() / 3600
            cursor = chunk_end

        return dict(result)

    @staticmethod
    def _point_lat_lon(point) -> tuple[float, float]:
        geom = to_shape(point.position)
        if not isinstance(geom, Point):
            raise ValueError("Expected Point geometry")
        return float(geom.y), float(geom.x)

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        earth_radius_km = 6371.0

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2

        return earth_radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))
