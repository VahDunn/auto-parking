import logging

from audit_service.ports.events import AUDIT_EVENTS_TOPIC, EventEnvelope, EventProducer

logger = logging.getLogger(__name__)


class AuditEventService:
    def __init__(
        self,
        producer: EventProducer,
        audit_topic: str = AUDIT_EVENTS_TOPIC,
    ) -> None:
        self._producer = producer
        self._audit_topic = audit_topic

    async def handle(self, event: EventEnvelope) -> None:
        await self._producer.publish(
            self._audit_topic,
            event,
            key=str(event.event_id),
        )
        logger.info(
            "Audit event routed: event_id=%s event_type=%s entity=%s entity_id=%s",
            event.event_id,
            event.event_type,
            event.entity,
            event.entity_id,
        )
