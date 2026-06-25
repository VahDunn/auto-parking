from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from event_bus.topics import AUDIT_EVENTS_TOPIC, GPS_EVENTS_TOPIC, VEHICLE_EVENTS_TOPIC

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

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["occurred_at"] = self.occurred_at.isoformat()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str | bytes) -> EventEnvelope:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventEnvelope:
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


class EventProducer(Protocol):
    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
        *,
        key: str | None = None,
    ) -> None:
        pass

    async def close(self) -> None:
        pass


class EventConsumer(Protocol):
    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        pass

    async def stop(self) -> None:
        pass


__all__ = [
    "AUDIT_EVENTS_TOPIC",
    "GPS_EVENTS_TOPIC",
    "VEHICLE_EVENTS_TOPIC",
    "EventConsumer",
    "EventEnvelope",
    "EventHandler",
    "EventProducer",
]
