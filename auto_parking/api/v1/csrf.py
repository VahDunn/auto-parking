from fastapi import APIRouter, Response

from auto_parking.core.security.auth import actor_dep
from auto_parking.core.security.csrf import new_csrf_token, set_csrf_cookie

router = APIRouter(tags=["security"])


@router.get("/csrf-token")
async def get_csrf_token(response: Response, actor=actor_dep):
    token = new_csrf_token()
    set_csrf_cookie(response, token, secure=False, samesite="lax")
    return {"csrf_token": token}
