from fastapi import APIRouter, HTTPException, WebSocket, status
from starlette.websockets import WebSocketDisconnect

from auto_parking.core.domain.enums import UserRole
from auto_parking.core.security.jwt import decode_access_token
from auto_parking.db.engine import AsyncSessionLocal
from auto_parking.realtime.gps import gps_realtime_hub
from auto_parking.repo.user import UserRepository

router = APIRouter()


@router.websocket("/live/ws")
async def live_tracking_websocket(websocket: WebSocket):
    token = websocket.cookies.get("access_token")
    if not token:
        await _reject_websocket(websocket)
        return

    try:
        payload = decode_access_token(token)
    except HTTPException:
        await _reject_websocket(websocket)
        return

    role = payload["role"]
    if role not in (UserRole.admin, UserRole.manager):
        await _reject_websocket(websocket)
        return

    enterprise_ids = await _visible_enterprise_ids(role=role, user_id=payload["id"])
    if role == UserRole.manager and enterprise_ids is None:
        await _reject_websocket(websocket)
        return

    await gps_realtime_hub.connect(websocket, enterprise_ids)
    try:
        await websocket.send_json({"event": "connected"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        gps_realtime_hub.disconnect(websocket)


async def _reject_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Authentication required",
    )


async def _visible_enterprise_ids(*, role: UserRole, user_id: int) -> set[int] | None:
    if role == UserRole.admin:
        return None
    async with AsyncSessionLocal() as session:
        return await UserRepository(session).get_visible_enterprise_ids(user_id)
