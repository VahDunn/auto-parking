import logging
from typing import TYPE_CHECKING

from audit_service.ports.events import EventEnvelope

if TYPE_CHECKING:
    from audit_service.repo.audit import AuditEventRepository

logger = logging.getLogger(__name__)


class AuditEventService:
    def __init__(self, repo: "AuditEventRepository") -> None:
        self._repo = repo

    async def handle(self, event: EventEnvelope) -> None:
        await self._repo.create_from_event(event)
        logger.info(
            "Audit event stored: event_id=%s event_type=%s entity=%s entity_id=%s",
            event.event_id,
            event.event_type,
            event.entity,
            event.entity_id,
        )
