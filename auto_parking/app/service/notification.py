from typing import TYPE_CHECKING, Any, Protocol

from auto_parking.app.filter import UserFilter
from auto_parking.core.domain.enums import NotificationType, UserRole
from auto_parking.core.domain.models import NotificationModel

if TYPE_CHECKING:
    from auto_parking.infrastructure.db.models import Notification, Trip
    from auto_parking.infrastructure.db.repositories.notification import NotificationRepository
    from auto_parking.infrastructure.db.repositories.user import UserRepository


class NotificationPublisher(Protocol):
    async def publish(self, user_id: int, notification: NotificationModel) -> None:
        pass


class NotificationService:
    def __init__(
        self,
        notification_repo: "NotificationRepository",
        user_repo: "UserRepository",
        publisher: NotificationPublisher | None = None,
    ):
        self._notification_repo = notification_repo
        self._user_repo = user_repo
        self._publisher = publisher

    async def get_for_user(
        self,
        *,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationModel]:
        notifications = await self._notification_repo.get_for_user(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        return [self._to_domain(notification) for notification in notifications]

    async def mark_read(
        self,
        *,
        user_id: int,
        notification_id: int,
    ) -> NotificationModel | None:
        notification = await self._notification_repo.mark_read(
            user_id=user_id,
            notification_id=notification_id,
        )
        return self._to_domain(notification) if notification else None

    async def mark_all_read(self, *, user_id: int) -> int:
        return await self._notification_repo.mark_all_read(user_id=user_id)

    async def unread_count(self, *, user_id: int) -> int:
        return await self._notification_repo.unread_count(user_id=user_id)

    async def notify_trip_created(self, trip: "Trip") -> list[NotificationModel]:
        enterprise_id = trip.vehicle.enterprise_id
        recipients = await self._user_repo.get(
            UserFilter(
                role=UserRole.manager,
                enterprise_id=enterprise_id,
            )
        )
        if not recipients:
            return []

        trip_id = trip.id
        vehicle_number = trip.vehicle.vehicle_number
        payloads = [
            self._trip_created_payload(
                recipient_user_id=recipient.id,
                enterprise_id=enterprise_id,
                trip_id=trip_id,
                vehicle_id=trip.vehicle_id,
                vehicle_number=vehicle_number,
            )
            for recipient in recipients
        ]
        notifications = [
            self._to_domain(notification)
            for notification in await self._notification_repo.create_many(payloads)
        ]

        if self._publisher is not None:
            for notification in notifications:
                await self._publisher.publish(
                    user_id=notification.recipient_user_id,
                    notification=notification,
                )

        return notifications

    @staticmethod
    def _trip_created_payload(
        *,
        recipient_user_id: int,
        enterprise_id: int,
        trip_id: int,
        vehicle_id: int,
        vehicle_number: str,
    ) -> dict[str, Any]:
        return {
            "recipient_user_id": recipient_user_id,
            "enterprise_id": enterprise_id,
            "trip_id": trip_id,
            "type": NotificationType.trip_created,
            "title": "Новая поездка",
            "body": f"Оформлена новая поездка автомобиля {vehicle_number}",
            "payload": {
                "trip_id": trip_id,
                "vehicle_id": vehicle_id,
                "vehicle_number": vehicle_number,
            },
        }

    @staticmethod
    def _to_domain(notification: "Notification") -> NotificationModel:
        return NotificationModel(
            id=notification.id,
            recipient_user_id=notification.recipient_user_id,
            enterprise_id=notification.enterprise_id,
            trip_id=notification.trip_id,
            type=NotificationType(notification.type),
            title=notification.title,
            body=notification.body,
            payload=dict(notification.payload),
            read_at=notification.read_at,
            created_at=notification.created_at,
        )
