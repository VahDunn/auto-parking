from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from audit_service.db.models import AuditEvent
from event_bus.contracts import EventEnvelope


class AuditEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_from_event(self, event: EventEnvelope) -> None:
        stmt = (
            insert(AuditEvent)
            .values(
                event_id=event.event_id,
                event_type=event.event_type,
                version=event.version,
                occurred_at=event.occurred_at,
                producer=event.producer,
                entity=event.entity,
                entity_id=str(event.entity_id) if event.entity_id is not None else None,
                correlation_id=event.correlation_id,
                payload=event.payload,
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
