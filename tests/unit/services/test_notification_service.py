from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.core.domain.enums import NotificationType
from auto_parking.filter import UserFilter
from auto_parking.service.notification import NotificationService

pytestmark = pytest.mark.asyncio


def notification_orm(recipient_user_id: int):
    return SimpleNamespace(
        id=recipient_user_id + 100,
        recipient_user_id=recipient_user_id,
        enterprise_id=4,
        trip_id=7,
        type="trip_created",
        title="Новая поездка",
        body="Оформлена новая поездка автомобиля А123ВС77",
        payload={
            "trip_id": 7,
            "vehicle_id": 5,
            "vehicle_number": "А123ВС77",
        },
        read_at=None,
        created_at=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
    )


async def test_notify_trip_created_creates_notifications_for_enterprise_managers():
    notification_repo = AsyncMock()
    user_repo = AsyncMock()
    publisher = AsyncMock()
    service = NotificationService(
        notification_repo=notification_repo,
        user_repo=user_repo,
        publisher=publisher,
    )

    user_repo.get.return_value = [
        SimpleNamespace(id=11),
        SimpleNamespace(id=12),
    ]
    notification_repo.create_many.return_value = [
        notification_orm(11),
        notification_orm(12),
    ]
    trip = SimpleNamespace(
        id=7,
        vehicle_id=5,
        vehicle=SimpleNamespace(
            enterprise_id=4,
            vehicle_number="А123ВС77",
        ),
    )

    result = await service.notify_trip_created(trip)

    assert [notification.recipient_user_id for notification in result] == [11, 12]
    assert result[0].type == NotificationType.trip_created
    user_repo.get.assert_awaited_once()
    filter_obj = user_repo.get.await_args.args[0]
    assert isinstance(filter_obj, UserFilter)
    assert filter_obj.role == "manager"
    assert filter_obj.enterprise_id == 4
    notification_repo.create_many.assert_awaited_once()
    payloads = notification_repo.create_many.await_args.args[0]
    assert [payload["recipient_user_id"] for payload in payloads] == [11, 12]
    assert payloads[0]["payload"]["vehicle_number"] == "А123ВС77"
    assert publisher.publish.await_count == 2


async def test_notify_trip_created_skips_when_enterprise_has_no_managers():
    notification_repo = AsyncMock()
    user_repo = AsyncMock()
    service = NotificationService(
        notification_repo=notification_repo,
        user_repo=user_repo,
    )

    user_repo.get.return_value = []
    trip = SimpleNamespace(
        id=7,
        vehicle_id=5,
        vehicle=SimpleNamespace(
            enterprise_id=4,
            vehicle_number="А123ВС77",
        ),
    )

    result = await service.notify_trip_created(trip)

    assert result == []
    notification_repo.create_many.assert_not_called()
