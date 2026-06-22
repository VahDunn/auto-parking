from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from aiokafka import AIOKafkaConsumer
from redis.asyncio import Redis
from redis.exceptions import RedisError

from notification_service.settings import Settings

VEHICLE_EVENTS_TOPIC = "auto-parking.vehicle.events"

logger = logging.getLogger(__name__)

EventHandler = Callable[["EventEnvelope"], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str
    event_type: str
    version: int
    occurred_at: datetime
    producer: str
    entity: str
    entity_id: int | str | None
    correlation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        producer: str,
        entity: str,
        entity_id: int | str | None,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        version: int = 1,
    ) -> EventEnvelope:
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            version=version,
            occurred_at=datetime.now(UTC),
            producer=producer,
            entity=entity,
            entity_id=entity_id,
            correlation_id=correlation_id,
            payload=payload or {},
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> EventEnvelope:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        occurred_at = data["occurred_at"]
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        return cls(
            event_id=str(data["event_id"]),
            event_type=str(data["event_type"]),
            version=int(data["version"]),
            occurred_at=occurred_at,
            producer=str(data["producer"]),
            entity=str(data["entity"]),
            entity_id=data.get("entity_id"),
            correlation_id=data.get("correlation_id"),
            payload=dict(data.get("payload") or {}),
        )


class EventConsumer(Protocol):
    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        pass

    async def stop(self) -> None:
        pass


class KafkaEventConsumer:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._consumer: AIOKafkaConsumer | None = None

    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset=self._auto_offset_reset,
            enable_auto_commit=False,
        )
        await self._consumer.start()
        try:
            async for message in self._consumer:
                try:
                    event = EventEnvelope.from_json(message.value)
                    await handler(event)
                    await self._consumer.commit()
                except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                    logger.warning("Invalid Kafka event payload", exc_info=True)
                    await self._consumer.commit()
                except Exception:
                    logger.exception(
                        "Kafka event handling failed: topic=%s partition=%s offset=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                    )
        finally:
            await self.stop()

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None


class RedisEventConsumer:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._stopping = False

    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(*topics)
            async for message in pubsub.listen():
                if self._stopping:
                    return
                if message["type"] != "message":
                    continue
                try:
                    event = EventEnvelope.from_json(message["data"])
                except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                    logger.warning("Invalid Redis event payload", exc_info=True)
                    continue
                await handler(event)
        except asyncio.CancelledError:
            raise
        except RedisError:
            logger.warning("Redis event consumer failed", exc_info=True)
            await asyncio.sleep(1)
            if not self._stopping:
                await self.subscribe(topics, handler)
        finally:
            await pubsub.aclose()

    async def stop(self) -> None:
        self._stopping = True
        await self._redis.aclose()


class NullEventConsumer:
    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        logger.warning("Event consumer disabled, topics ignored: %s", ", ".join(topics))
        while True:
            await asyncio.sleep(3600)

    async def stop(self) -> None:
        return None


def create_event_consumer(settings: Settings) -> EventConsumer:
    backend = settings.event_bus_backend.lower()
    if backend == "kafka":
        return KafkaEventConsumer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_notification_consumer_group,
        )
    if backend == "redis" and settings.redis_url:
        redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        return RedisEventConsumer(redis)
    return NullEventConsumer()
