import logging

from notification_service.ports.events import EventEnvelope
from notification_service.ports.manager_lookup import ManagerLookup
from notification_service.ports.telegram import TelegramSender
from notification_service.ports.telegram_sessions import TelegramSessionRegistry

logger = logging.getLogger(__name__)


class VehicleEventNotificationService:
    def __init__(
        self,
        *,
        manager_lookup: ManagerLookup,
        telegram_session_registry: TelegramSessionRegistry,
        telegram_sender: TelegramSender,
    ) -> None:
        self._manager_lookup = manager_lookup
        self._telegram_session_registry = telegram_session_registry
        self._telegram_sender = telegram_sender

    async def handle(self, event: EventEnvelope) -> None:
        if event.entity != "vehicle" or not event.event_type.startswith("vehicle."):
            return

        enterprise_id = self._enterprise_id(event)
        if enterprise_id is None:
            logger.info("Vehicle event skipped without enterprise_id: event_id=%s", event.event_id)
            return

        manager_ids = await self._manager_lookup.manager_ids_for_enterprise(enterprise_id)
        if not manager_ids:
            return

        text = self._message_text(event)
        for manager_id in manager_ids:
            chat_id = await self._telegram_session_registry.get_telegram_chat_id(
                user_id=manager_id,
            )
            if chat_id is None:
                continue
            await self._telegram_sender.send_message(chat_id=chat_id, text=text)

    @staticmethod
    def _enterprise_id(event: EventEnvelope) -> int | None:
        value = event.payload.get("enterprise_id")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

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
