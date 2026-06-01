import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from starlette.websockets import WebSocketDisconnect

from auto_parking.api.schemas.notification import (
    NotificationOut,
    NotificationReadAllOut,
    NotificationUnreadCountOut,
)
from auto_parking.core.domain.enums import UserRole
from auto_parking.core.security.actor import Actor
from auto_parking.core.security.jwt import decode_access_token
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.notifications import (
    fetch_unread_notifications_for_websocket,
    notification_publisher,
)
from auto_parking.deps.services import dep_notification_service
from auto_parking.service.notification import NotificationService

router = APIRouter()
dep_actor_guard = Depends(require_manager_or_higher)


@router.get(
    "",
    response_model=list[NotificationOut],
)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Actor = dep_actor_guard,
    service: NotificationService = dep_notification_service,
):
    return await service.get_for_user(
        user_id=actor.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountOut,
)
async def get_unread_count(
    actor: Actor = dep_actor_guard,
    service: NotificationService = dep_notification_service,
):
    return NotificationUnreadCountOut(unread_count=await service.unread_count(user_id=actor.id))


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
)
async def mark_notification_read(
    notification_id: int,
    actor: Actor = dep_actor_guard,
    service: NotificationService = dep_notification_service,
):
    notification = await service.mark_read(
        user_id=actor.id,
        notification_id=notification_id,
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return notification


@router.patch(
    "/read-all",
    response_model=NotificationReadAllOut,
)
async def mark_all_notifications_read(
    actor: Actor = dep_actor_guard,
    service: NotificationService = dep_notification_service,
):
    return NotificationReadAllOut(updated_count=await service.mark_all_read(user_id=actor.id))


@router.websocket("/ws")
async def notifications_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    actor = Actor(role=payload["role"], id=payload["id"])
    if actor.role not in (UserRole.admin, UserRole.manager):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await notification_publisher.connect(actor.id, websocket)
    try:
        await websocket.send_json({"event": "connected"})
        await _send_unread_notifications(websocket, actor.id)
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1)
            except TimeoutError:
                await _send_unread_notifications(websocket, actor.id)
    except WebSocketDisconnect:
        notification_publisher.disconnect(actor.id, websocket)


async def _send_unread_notifications(
    websocket: WebSocket,
    user_id: int,
) -> None:
    notifications = await fetch_unread_notifications_for_websocket(
        user_id=user_id,
        limit=50,
    )
    for notification in reversed(notifications):
        await notification_publisher.send_if_new(websocket, notification)
