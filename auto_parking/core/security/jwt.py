from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from jose import JWTError, jwt

from auto_parking.core.config import settings
from auto_parking.core.enums.user_role import UserRole

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TTL_MINUTES = settings.jwt_access_ttl_minutes


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _create_token(
    *,
    actor_type: str,
    actor_id: int,
    token_type: Literal["access", "refresh"],
    expires_minutes: int,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": f"{actor_type}:{actor_id}",
        "actor_type": actor_type,
        "actor_id": actor_id,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(
    *, actor_type: str, actor_id: int, expires_minutes: int | None = None
) -> str:
    return _create_token(
        actor_type=actor_type,
        actor_id=actor_id,
        token_type="access",
        expires_minutes=expires_minutes or ACCESS_TTL_MINUTES,
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token.strip(), SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise _unauthorized(f"Invalid or expired token: {e}") from None


def decode_access_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise _unauthorized("Wrong token type")

    actor_type = payload.get("actor_type")
    actor_id = payload.get("actor_id")

    if not isinstance(actor_type, str) or not isinstance(actor_id, int):
        raise _unauthorized("Invalid token payload")

    try:
        role = UserRole(actor_type)
    except ValueError:
        raise _unauthorized("Invalid token payload") from None

    return {"role": role, "id": actor_id}
