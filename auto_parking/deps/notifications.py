from fastapi import WebSocket

from auto_parking.api.schemas.notification import NotificationOut
from auto_parking.core.domain.models import NotificationModel
from auto_parking.db.engine import AsyncSessionLocal
from auto_parking.repo.notification import NotificationRepository
from auto_parking.repo.user import UserRepository
from auto_parking.service.notification import NotificationService


class WebSocketNotificationPublisher:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        self._sent_ids: dict[WebSocket, set[int]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)
        self._sent_ids.setdefault(websocket, set())

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if connections is None:
            return
        connections.discard(websocket)
        self._sent_ids.pop(websocket, None)
        if not connections:
            self._connections.pop(user_id, None)

    async def publish(self, user_id: int, notification: NotificationModel) -> None:
        for websocket in tuple(self._connections.get(user_id, ())):
            await self.send_if_new(websocket, notification)

    async def send_if_new(
        self,
        websocket: WebSocket,
        notification: NotificationModel,
    ) -> None:
        sent_ids = self._sent_ids.setdefault(websocket, set())
        if notification.id is not None and notification.id in sent_ids:
            return

        payload = {
            "event": "notification.created",
            "notification": NotificationOut.model_validate(notification).model_dump(mode="json"),
        }
        try:
            await websocket.send_json(payload)
        except RuntimeError:
            self._sent_ids.pop(websocket, None)
        else:
            if notification.id is not None:
                sent_ids.add(notification.id)


notification_publisher = WebSocketNotificationPublisher()


async def fetch_unread_notifications_for_websocket(
    *,
    user_id: int,
    limit: int = 50,
) -> list[NotificationModel]:
    async with AsyncSessionLocal() as session:
        service = NotificationService(
            notification_repo=NotificationRepository(session),
            user_repo=UserRepository(session),
        )
        return await service.get_for_user(
            user_id=user_id,
            unread_only=True,
            limit=limit,
            offset=0,
        )
