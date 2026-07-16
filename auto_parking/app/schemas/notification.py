from datetime import datetime
from typing import Any

from auto_parking.app.schemas.base import ApiSchema
from auto_parking.core.domain.enums import NotificationType


class NotificationOut(ApiSchema):
    id: int
    recipient_user_id: int
    enterprise_id: int
    trip_id: int
    type: NotificationType
    title: str
    body: str
    payload: dict[str, Any]
    read_at: datetime | None = None
    created_at: datetime


class NotificationReadAllOut(ApiSchema):
    updated_count: int


class NotificationUnreadCountOut(ApiSchema):
    unread_count: int
