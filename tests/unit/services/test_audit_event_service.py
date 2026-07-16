import json
from datetime import UTC

import pytest

from audit_service.service import AuditEventService
from event_bus.contracts import EventEnvelope

pytestmark = pytest.mark.asyncio


class FakeAuditEventRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self.events: list[EventEnvelope] = []
        self._error = error

    async def create_from_event(self, event: EventEnvelope) -> None:
        if self._error is not None:
            raise self._error
        self.events.append(event)


async def test_audit_event_service_stores_event():
    repo = FakeAuditEventRepository()
    service = AuditEventService(repo)
    event = EventEnvelope.create(
        event_type="vehicle.updated",
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=7,
        payload={
            "vehicle_id": 7,
            "vehicle_number": "А123ВС77",
            "enterprise_id": 2,
        },
    )

    await service.handle(event)

    assert repo.events == [event]


async def test_audit_event_service_stores_any_event_type():
    repo = FakeAuditEventRepository()
    service = AuditEventService(repo)
    event = EventEnvelope.create(
        event_type="vehicle.deleted",
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=7,
        payload={"vehicle_id": 7},
    )

    await service.handle(event)

    assert repo.events == [event]


async def test_audit_event_service_propagates_repository_errors():
    service = AuditEventService(FakeAuditEventRepository(RuntimeError("db is down")))
    event = EventEnvelope.create(
        event_type="vehicle.updated",
        producer="auto-parking-api",
        entity="vehicle",
        entity_id=7,
    )

    with pytest.raises(RuntimeError, match="db is down"):
        await service.handle(event)


async def test_audit_event_envelope_from_json_parses_contract():
    event = EventEnvelope.from_json(
        json.dumps(
            {
                "event_id": "event-1",
                "event_type": "vehicle.updated",
                "version": 1,
                "occurred_at": "2026-06-23T10:20:30+00:00",
                "producer": "auto-parking-api",
                "entity": "vehicle",
                "entity_id": 7,
                "correlation_id": "request-1",
                "payload": {
                    "vehicle_id": 7,
                    "vehicle_number": "А123ВС77",
                    "enterprise_id": 2,
                },
            }
        )
    )

    assert event.event_id == "event-1"
    assert event.event_type == "vehicle.updated"
    assert event.occurred_at.tzinfo == UTC
    assert event.payload["vehicle_number"] == "А123ВС77"
