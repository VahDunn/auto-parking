from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, status

from auto_parking.core.security.bearer import get_token
from auto_parking.core.security.jwt import decode_access_token

ActorType = Literal["admin", "manager"]


@dataclass(frozen=True)
class Actor:
    type: ActorType
    id: int


async def get_current_actor(token: str = Depends(get_token)) -> Actor:
    sub = decode_access_token(token)
    try:
        return Actor(type=sub["type"], id=int(sub["id"]))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


current_actor_dep = Depends(get_current_actor)
