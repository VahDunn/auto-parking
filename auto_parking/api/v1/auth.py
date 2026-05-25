from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from auto_parking.core.security.jwt import create_access_token
from auto_parking.core.security.passwords import verify_password
from auto_parking.deps.services import dep_user_service
from auto_parking.filter import UserFilter

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
