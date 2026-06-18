from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from auto_parking.core.domain.enums import NotificationType, UserRole
from auto_parking.core.domain.models import NotificationModel
from auto_parking.core.security.jwt import create_access_token
from auto_parking.main import app as fastapi_app
from tests.conftest import (
    set_actor_override,
    set_notification_service_override,
)


def make_notification(notification_id: int = 1) -> NotificationModel:
    return NotificationModel(
        id=notification_id,
        recipient_user_id=12,
        enterprise_id=4,
        trip_id=7,
        type=NotificationType.trip_created,
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


@pytest.mark.asyncio
async def test_list_notifications(client, overrides, notification_service_mock):
    set_actor_override(overrides, UserRole.manager, actor_id=12)
    set_notification_service_override(overrides, notification_service_mock)
    notification_service_mock.get_for_user.return_value = [make_notification()]

    response = await client.get(
        "/api/notifications",
        params={"unread_only": "true", "limit": 20, "offset": 5},
    )

    assert response.status_code == 200
    assert response.json()[0]["type"] == "trip_created"
    assert response.json()[0]["payload"]["vehicle_number"] == "А123ВС77"
    notification_service_mock.get_for_user.assert_awaited_once_with(
        user_id=12,
        unread_only=True,
        limit=20,
        offset=5,
    )


@pytest.mark.asyncio
async def test_mark_notification_read(client, overrides, notification_service_mock):
    set_actor_override(overrides, UserRole.manager, actor_id=12)
    set_notification_service_override(overrides, notification_service_mock)
    notification = make_notification()
    notification.read_at = datetime(2026, 5, 28, 10, 10, tzinfo=UTC)
    notification_service_mock.mark_read.return_value = notification

    response = await client.patch("/api/notifications/1/read")

    assert response.status_code == 200
    assert response.json()["read_at"] == "2026-05-28T10:10:00Z"
    notification_service_mock.mark_read.assert_awaited_once_with(
        user_id=12,
        notification_id=1,
    )


@pytest.mark.asyncio
async def test_mark_notification_read_returns_404(
    client,
    overrides,
    notification_service_mock,
):
    set_actor_override(overrides, UserRole.manager, actor_id=12)
    set_notification_service_override(overrides, notification_service_mock)
    notification_service_mock.mark_read.return_value = None

    response = await client.patch("/api/notifications/999/read")

    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


@pytest.mark.asyncio
async def test_mark_all_notifications_read(client, overrides, notification_service_mock):
    set_actor_override(overrides, UserRole.manager, actor_id=12)
    set_notification_service_override(overrides, notification_service_mock)
    notification_service_mock.mark_all_read.return_value = 3

    response = await client.patch("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.json() == {"updated_count": 3}


@pytest.mark.asyncio
async def test_get_unread_count(client, overrides, notification_service_mock):
    set_actor_override(overrides, UserRole.manager, actor_id=12)
    set_notification_service_override(overrides, notification_service_mock)
    notification_service_mock.unread_count.return_value = 2

    response = await client.get("/api/notifications/unread-count")

    assert response.status_code == 200
    assert response.json() == {"unread_count": 2}


def test_notifications_websocket_authenticates_from_cookie(monkeypatch):
    monkeypatch.setattr(
        "auto_parking.api.v1.notifications.fetch_unread_notifications_for_websocket",
        AsyncMock(return_value=[]),
    )
    token = create_access_token(actor_type=UserRole.manager.value, actor_id=12)

    with TestClient(fastapi_app) as client:
        client.cookies.set("access_token", token)
        with client.websocket_connect("/api/notifications/ws") as websocket:
            assert websocket.receive_json() == {"event": "connected"}


def test_notifications_websocket_rejects_query_token(monkeypatch):
    monkeypatch.setattr(
        "auto_parking.api.v1.notifications.fetch_unread_notifications_for_websocket",
        AsyncMock(return_value=[]),
    )
    token = create_access_token(actor_type=UserRole.manager.value, actor_id=12)

    with TestClient(fastapi_app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/notifications/ws?token={token}") as websocket:
                websocket.receive_json()

    assert exc_info.value.code == 1008
