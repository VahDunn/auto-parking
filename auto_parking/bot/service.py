from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import atan2, cos, radians, sin, sqrt

from auto_parking.bot.api_client import AutoParkingApiClient


@dataclass(slots=True)
class BotSession:
    username: str
    access_token: str


@dataclass(slots=True)
class MileageSummary:
    title: str
    date_from: datetime
    date_to: datetime
    trips_count: int
    distance_km: float


@dataclass(slots=True)
class EnterpriseLookup:
    enterprise: dict | None
    matches: list[dict]


@dataclass(slots=True)
class VehicleLookup:
    vehicle: dict | None
    matches: list[dict]


class BotService:
    def __init__(self, api_client: AutoParkingApiClient) -> None:
        self._api_client = api_client

    async def login(self, username: str, password: str) -> BotSession | None:
        token = await self._api_client.login(username=username, password=password)
        if token is None:
            return None

        return BotSession(username=username, access_token=token)

    async def vehicle_mileage(
        self,
        *,
        session: BotSession,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> MileageSummary | None:
        vehicle = await self._api_client.get_vehicle(session.access_token, vehicle_id)
        if vehicle is None:
            return None

        trips = await self._api_client.get_vehicle_trips(
            token=session.access_token,
            vehicle_id=vehicle_id,
            date_from=date_from,
            date_to=date_to,
        )
        if trips is None:
            return None

        return MileageSummary(
            title=f"Автомобиль #{vehicle_id}",
            date_from=date_from,
            date_to=date_to,
            trips_count=len(trips),
            distance_km=self._trips_distance_km(trips),
        )

    async def find_vehicle_by_number_prefix(
        self,
        *,
        session: BotSession,
        number_prefix: str,
    ) -> VehicleLookup:
        prefix = number_prefix.strip()
        if not prefix:
            return VehicleLookup(vehicle=None, matches=[])

        matches = await self._api_client.get_vehicles_by_number_prefix(
            session.access_token,
            prefix,
        )
        if len(matches) == 1:
            return VehicleLookup(vehicle=matches[0], matches=matches)

        return VehicleLookup(vehicle=None, matches=matches)

    async def enterprise_mileage(
        self,
        *,
        session: BotSession,
        enterprise_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> MileageSummary | None:
        vehicles = await self._api_client.get_enterprise_vehicles(
            token=session.access_token,
            enterprise_id=enterprise_id,
        )
        if not vehicles:
            return MileageSummary(
                title=f"Предприятие #{enterprise_id}",
                date_from=date_from,
                date_to=date_to,
                trips_count=0,
                distance_km=0.0,
            )

        all_trips: list[dict] = []
        for vehicle in vehicles:
            trips = await self._api_client.get_vehicle_trips(
                token=session.access_token,
                vehicle_id=vehicle["id"],
                date_from=date_from,
                date_to=date_to,
            )
            if trips:
                all_trips.extend(trips)

        return MileageSummary(
            title=f"Предприятие #{enterprise_id}",
            date_from=date_from,
            date_to=date_to,
            trips_count=len(all_trips),
            distance_km=self._trips_distance_km(all_trips),
        )

    async def find_enterprise_by_name_prefix(
        self,
        *,
        session: BotSession,
        name_prefix: str,
    ) -> EnterpriseLookup:
        prefix = name_prefix.strip().casefold()
        if not prefix:
            return EnterpriseLookup(enterprise=None, matches=[])

        enterprises = await self._api_client.get_enterprises(session.access_token)
        matches = [
            enterprise
            for enterprise in enterprises
            if str(enterprise.get("name") or "").casefold().startswith(prefix)
        ]

        if len(matches) == 1:
            return EnterpriseLookup(enterprise=matches[0], matches=matches)

        return EnterpriseLookup(enterprise=None, matches=matches)

    @classmethod
    def _trips_distance_km(cls, trips: list[dict]) -> float:
        return round(sum(cls._trip_distance_km(trip) for trip in trips), 3)

    @staticmethod
    def _trip_distance_km(trip: dict) -> float:
        start_point = trip.get("start_point")
        end_point = trip.get("end_point")
        if not start_point or not end_point:
            return 0.0

        start_lat, start_lon = start_point["latitude"], start_point["longitude"]
        end_lat, end_lon = end_point["latitude"], end_point["longitude"]
        return BotService._haversine_km(start_lat, start_lon, end_lat, end_lon)

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        earth_radius_km = 6371.0

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return earth_radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))


def day_range(value: str) -> tuple[datetime, datetime]:
    date_value = datetime.strptime(value, "%Y-%m-%d").date()
    date_from = datetime.combine(date_value, datetime.min.time(), tzinfo=UTC)
    return date_from, date_from + timedelta(days=1)


def month_range(value: str) -> tuple[datetime, datetime]:
    date_value = datetime.strptime(value, "%Y-%m").date()
    date_from = datetime(date_value.year, date_value.month, 1, tzinfo=UTC)
    if date_value.month == 12:
        return date_from, datetime(date_value.year + 1, 1, 1, tzinfo=UTC)
    return date_from, datetime(date_value.year, date_value.month + 1, 1, tzinfo=UTC)


def format_mileage_summary(summary: MileageSummary) -> str:
    rounded_distance_km = round(summary.distance_km)
    return (
        f"{summary.title}\n"
        f"Период: {summary.date_from:%Y-%m-%d %H:%M} - {summary.date_to:%Y-%m-%d %H:%M} UTC\n"
        f"Поездок: {summary.trips_count}\n"
        f"Пробег: {rounded_distance_km} км"
    )
