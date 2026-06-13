import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime

import reactivex.operators as ops
from fastapi import WebSocket
from reactivex.subject import Subject
from redis.asyncio import Redis
from redis.exceptions import RedisError

from auto_parking.core.config import settings

logger = logging.getLogger(__name__)

GPS_CHANNEL = "auto-parking:vehicle-gps"


@dataclass(frozen=True)
class GpsPointEvent:
    vehicle_id: int
    vehicle_number: str
    enterprise_id: int
    recorded_at_utc: str
    latitude: float
    longitude: float

    @classmethod
    def from_payload(cls, payload: dict) -> "GpsPointEvent":
        return cls(
            vehicle_id=int(payload["vehicle_id"]),
            vehicle_number=str(payload["vehicle_number"]),
            enterprise_id=int(payload["enterprise_id"]),
            recorded_at_utc=str(payload["recorded_at_utc"]),
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
        )


def _valid_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    required = {
        "vehicle_id",
        "vehicle_number",
        "enterprise_id",
        "recorded_at_utc",
        "latitude",
        "longitude",
    }
    if not required.issubset(payload):
        return False
    if not isinstance(payload["vehicle_number"], str) or not payload["vehicle_number"].strip():
        return False
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        datetime.fromisoformat(str(payload["recorded_at_utc"]).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


async def publish_gps_point(
    redis: Redis | None,
    *,
    vehicle_id: int,
    vehicle_number: str,
    enterprise_id: int,
    recorded_at_utc: datetime,
    latitude: float,
    longitude: float,
) -> None:
    if redis is None:
        return
    payload = GpsPointEvent(
        vehicle_id=vehicle_id,
        vehicle_number=vehicle_number,
        enterprise_id=enterprise_id,
        recorded_at_utc=recorded_at_utc.isoformat(),
        latitude=latitude,
        longitude=longitude,
    )
    try:
        await redis.publish(GPS_CHANNEL, json.dumps(asdict(payload)))
    except RedisError:
        logger.warning("Failed to publish GPS event", exc_info=True)


def create_gps_redis() -> Redis | None:
    if not settings.redis_url:
        return None
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


class GpsRealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, set[int] | None] = {}
        self._subject: Subject = Subject()
        self._subscription = self._subject.pipe(
            ops.filter(_valid_payload),
            ops.map(GpsPointEvent.from_payload),
            ops.distinct_until_changed(
                key_mapper=lambda event: (
                    event.vehicle_id,
                    event.recorded_at_utc,
                    event.latitude,
                    event.longitude,
                )
            ),
        ).subscribe(on_next=self._schedule_broadcast, on_error=self._log_pipeline_error)
        self._listener_task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        if self._listener_task is None and settings.redis_url:
            self._stopping = False
            self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        self._stopping = True
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

    async def connect(self, websocket: WebSocket, enterprise_ids: set[int] | None) -> None:
        await websocket.accept()
        self._connections[websocket] = enterprise_ids

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    def emit(self, payload: dict) -> None:
        self._subject.on_next(payload)

    def _schedule_broadcast(self, event: GpsPointEvent) -> None:
        asyncio.get_running_loop().create_task(self._broadcast(event))

    async def _broadcast(self, event: GpsPointEvent) -> None:
        payload = {"event": "vehicle.gps", "point": asdict(event)}
        for websocket, enterprise_ids in tuple(self._connections.items()):
            if enterprise_ids is not None and event.enterprise_id not in enterprise_ids:
                continue
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                self.disconnect(websocket)

    async def _listen(self) -> None:
        while not self._stopping:
            redis = create_gps_redis()
            if redis is None:
                return
            pubsub = redis.pubsub()
            try:
                await pubsub.subscribe(GPS_CHANNEL)
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        payload = json.loads(message["data"])
                    except (TypeError, json.JSONDecodeError):
                        continue
                    self.emit(payload)
            except asyncio.CancelledError:
                raise
            except RedisError:
                logger.warning("GPS Redis listener disconnected", exc_info=True)
                await asyncio.sleep(1)
            finally:
                await pubsub.aclose()
                await redis.aclose()

    @staticmethod
    def _log_pipeline_error(error: Exception) -> None:
        logger.error("GPS reactive pipeline failed: %s", error)


gps_realtime_hub = GpsRealtimeHub()
