from typing import TYPE_CHECKING

from auto_parking.ports.events import EventEnvelope

if TYPE_CHECKING:
    from auto_parking.repo.audit import AuditEventRepository


class AuditEventService:
    def __init__(self, repo: "AuditEventRepository") -> None:
        self._repo = repo

    async def store(self, event: EventEnvelope) -> None:
        await self._repo.create_from_event(event)
