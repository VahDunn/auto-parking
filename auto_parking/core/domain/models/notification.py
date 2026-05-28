from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from auto_parking.core.domain.enums.notification_type import NotificationType
from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class NotificationModel(DomainModel):
    id: int | None
    recipient_user_id: int
    enterprise_id: int
    trip_id: int
    type: NotificationType
    title: str
    body: str
    payload: dict[str, Any] = field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime | None = None
