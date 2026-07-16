from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from time import perf_counter

from auto_parking.app.ports.cache import CacheClient
from auto_parking.app.service.bot_session_registry import BotSessionRegistry
from auto_parking.bot.api_client import AutoParkingApiClient
from auto_parking.core.security.jwt import decode_access_token
from auto_parking.infrastructure.observability.performance import log_cache_lookup


@dataclass(slots=True)
class BotSession:
    username: str
    access_token: str
    user_id: int
    role: str


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
    def __init__(
        self,
        api_client: AutoParkingApiClient,
        cache: CacheClient | None = None,
        cache_ttl_seconds: int = 300,
        bot_login_registry_ttl_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        self._api_client = api_client
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._bot_login_registry_ttl_seconds = bot_login_registry_ttl_seconds

    async def login(self, username: str, password: str) -> BotSession | None:
        token = await self._api_client.login(username=username, password=password)
        if token is None:
            return None

        try:
            actor = decode_access_token(token)
        except Exception:
            return None
        return BotSession(
            username=username,
            access_token=token,
            user_id=actor["id"],
            role=actor["role"].value,
        )

    async def bind_telegram_chat(
        self,
        *,
        chat_id: int,
        session: BotSession,
    ) -> None:
        if self._cache is None:
            return
        registry = BotSessionRegistry(
            self._cache,
            ttl_seconds=self._bot_login_registry_ttl_seconds,
        )
        await registry.bind_telegram_chat(
            user_id=session.user_id,
            chat_id=chat_id,
            username=session.username,
            role=session.role,
        )

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

        cache_key = self._mileage_cache_key(
            session=session,
            target="vehicle",
            target_id=vehicle_id,
            date_from=date_from,
            date_to=date_to,
        )
        cached = await self._get_cached_summary(cache_key)
        if cached is not None:
            return cached

        trips = await self._api_client.get_vehicle_trips(
            token=session.access_token,
            vehicle_id=vehicle_id,
            date_from=date_from,
            date_to=date_to,
        )
        if trips is None:
            return None

        summary = MileageSummary(
            title=f"Автомобиль #{vehicle_id}",
            date_from=date_from,
            date_to=date_to,
            trips_count=len(trips),
            distance_km=self._trips_distance_km(trips),
        )
        await self._cache_summary(cache_key, summary)
        return summary

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
        enterprise = await self._api_client.get_enterprise(session.access_token, enterprise_id)
        if enterprise is None:
            return None

        cache_key = self._mileage_cache_key(
            session=session,
            target="enterprise",
            target_id=enterprise_id,
            date_from=date_from,
            date_to=date_to,
        )
        cached = await self._get_cached_summary(cache_key)
        if cached is not None:
            return cached

        vehicles = await self._api_client.get_enterprise_vehicles(
            token=session.access_token,
            enterprise_id=enterprise_id,
        )
        if not vehicles:
            summary = MileageSummary(
                title=f"Предприятие #{enterprise_id}",
                date_from=date_from,
                date_to=date_to,
                trips_count=0,
                distance_km=0.0,
            )
            await self._cache_summary(cache_key, summary)
            return summary

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

        summary = MileageSummary(
            title=f"Предприятие #{enterprise_id}",
            date_from=date_from,
            date_to=date_to,
            trips_count=len(all_trips),
            distance_km=self._trips_distance_km(all_trips),
        )
        await self._cache_summary(cache_key, summary)
        return summary

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

    async def unread_notifications(self, *, session: BotSession) -> list[dict]:
        return await self._api_client.get_unread_notifications(session.access_token)

    async def mark_notification_read(
        self,
        *,
        session: BotSession,
        notification_id: int,
    ) -> dict | None:
        return await self._api_client.mark_notification_read(
            session.access_token,
            notification_id,
        )

    async def mark_all_notifications_read(self, *, session: BotSession) -> bool:
        return await self._api_client.mark_all_notifications_read(session.access_token)

    @staticmethod
    def _mileage_cache_key(
        *,
        session: BotSession,
        target: str,
        target_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> str:
        return (
            f"bot:mileage:{session.username}:{target}:{target_id}:"
            f"{date_from.isoformat()}:{date_to.isoformat()}"
        )

    async def _get_cached_summary(self, key: str) -> MileageSummary | None:
        if self._cache is None:
            return None

        started_at = perf_counter()
        try:
            cached = await self._cache.get_text(key)
        except Exception:
            log_cache_lookup(
                operation="bot_mileage_summary",
                result="error",
                duration_seconds=perf_counter() - started_at,
            )
            return None

        if cached is None:
            log_cache_lookup(
                operation="bot_mileage_summary",
                result="miss",
                duration_seconds=perf_counter() - started_at,
            )
            return None

        log_cache_lookup(
            operation="bot_mileage_summary",
            result="hit",
            duration_seconds=perf_counter() - started_at,
        )
        data = json.loads(cached)
        return MileageSummary(
            title=data["title"],
            date_from=datetime.fromisoformat(data["date_from"]),
            date_to=datetime.fromisoformat(data["date_to"]),
            trips_count=data["trips_count"],
            distance_km=data["distance_km"],
        )

    async def _cache_summary(self, key: str, summary: MileageSummary) -> None:
        if self._cache is None:
            return None

        value = json.dumps(
            {
                "title": summary.title,
                "date_from": summary.date_from.isoformat(),
                "date_to": summary.date_to.isoformat(),
                "trips_count": summary.trips_count,
                "distance_km": summary.distance_km,
            }
        )
        try:
            await self._cache.set_text(
                key,
                value,
                ttl_seconds=self._cache_ttl_seconds,
            )
        except Exception:
            return None

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
