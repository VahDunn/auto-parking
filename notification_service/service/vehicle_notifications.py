import logging

from event_bus.contracts import AUDIT_EVENTS_TOPIC, EventEnvelope, EventProducer
from notification_service.ports.telegram import TelegramSender
from notification_service.ports.telegram_sessions import TelegramSessionRegistry

logger = logging.getLogger(__name__)


class VehicleEventNotificationService:
    def __init__(
        self,
        *,
        telegram_session_registry: TelegramSessionRegistry,
        telegram_sender: TelegramSender,
        audit_event_producer: EventProducer | None = None,
        audit_topic: str = AUDIT_EVENTS_TOPIC,
    ) -> None:
        self._telegram_session_registry = telegram_session_registry
        self._telegram_sender = telegram_sender
        self._audit_event_producer = audit_event_producer
        self._audit_topic = audit_topic

    async def handle(self, event: EventEnvelope) -> None:
        if event.entity != "vehicle" or not event.event_type.startswith("vehicle."):
            return

        manager_ids = self._manager_user_ids(event)
        if not manager_ids:
            return

        text = self._message_text(event)
        for manager_id in manager_ids:
            chat_id = await self._telegram_session_registry.get_telegram_chat_id(
                user_id=manager_id,
            )
            if chat_id is None:
                continue
            sent = await self._telegram_sender.send_message(chat_id=chat_id, text=text)
            await self._publish_audit_event(
                source_event=event,
                manager_id=manager_id,
                chat_id=chat_id,
                text=text,
                sent=sent,
            )

    async def _publish_audit_event(
        self,
        *,
        source_event: EventEnvelope,
        manager_id: int,
        chat_id: int,
        text: str,
        sent: bool,
    ) -> None:
        if self._audit_event_producer is None:
            return

        vehicle_id = source_event.payload.get("vehicle_id") or source_event.entity_id
        vehicle_number = source_event.payload.get("vehicle_number")
        event = EventEnvelope.create(
            event_type="notification.telegram.sent" if sent else "notification.telegram.failed",
            producer="notification-service",
            entity="telegram_notification",
            entity_id=manager_id,
            correlation_id=source_event.event_id,
            payload={
                "manager_user_id": manager_id,
                "telegram_chat_id": chat_id,
                "vehicle_id": vehicle_id,
                "vehicle_number": vehicle_number,
                "source_event_id": source_event.event_id,
                "source_event_type": source_event.event_type,
                "message_text": text,
                "result": "sent" if sent else "failed",
            },
        )
        try:
            await self._audit_event_producer.publish(
                self._audit_topic,
                event,
                key=str(manager_id),
            )
        except Exception:
            logger.warning(
                "Failed to publish notification audit event: source_event_id=%s manager_id=%s",
                source_event.event_id,
                manager_id,
                exc_info=True,
            )

    @staticmethod
    def _manager_user_ids(event: EventEnvelope) -> list[int]:
        raw_ids = event.payload.get("manager_user_ids") or []
        if not isinstance(raw_ids, list):
            logger.info(
                "Vehicle event skipped with invalid manager_user_ids: event_id=%s",
                event.event_id,
            )
            return []

        manager_ids: list[int] = []
        for raw_id in raw_ids:
            try:
                manager_ids.append(int(raw_id))
            except (TypeError, ValueError):
                logger.info(
                    "Vehicle event contains invalid manager_user_id: event_id=%s raw_id=%s",
                    event.event_id,
                    raw_id,
                )
        return manager_ids

    @staticmethod
    def _message_text(event: EventEnvelope) -> str:
        vehicle_id = event.payload.get("vehicle_id") or event.entity_id
        vehicle_number = event.payload.get("vehicle_number") or f"#{vehicle_id}"
        action = {
            "vehicle.created": "создан",
            "vehicle.updated": "обновлен",
            "vehicle.deleted": "удален",
        }.get(event.event_type, "изменен")
        return f"Автомобиль {vehicle_number}: {action}."
