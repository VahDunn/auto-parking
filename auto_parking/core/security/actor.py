from dataclasses import dataclass

from fastapi import Depends

from auto_parking.core.domain.user_role import UserRole
from auto_parking.core.security.bearer import get_token
from auto_parking.core.security.jwt import decode_access_token


@dataclass(frozen=True)
class Actor:
    role: UserRole
    id: int


async def get_current_actor(token: str = Depends(get_token)) -> Actor:
    payload = decode_access_token(token)
    return Actor(role=payload["role"], id=payload["id"])


current_actor_dep = Depends(get_current_actor)
