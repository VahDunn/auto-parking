from fastapi import APIRouter, HTTPException, Response, status

from auto_parking.app.deps.services import dep_user_service
from auto_parking.app.filter import UserFilter
from auto_parking.app.schemas.auth import LoginRequest, TokenResponse
from auto_parking.core.security.jwt import create_access_token
from auto_parking.core.security.passwords import verify_password

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    user_service=dep_user_service,
):
    users = await user_service.get(UserFilter(username=data.username))
    user = users[0] if users else None

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong login or password"
        )

    token = create_access_token(actor_type=user.role.value, actor_id=user.id)

    response.set_cookie(
        path="/",
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return TokenResponse(access_token=token)
