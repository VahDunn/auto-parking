from fastapi import HTTPException, status

from auto_parking.core.domain.user_role import UserRole
from auto_parking.db.models import User
from auto_parking.deps.commons import dep_actor
from auto_parking.deps.services import dep_user_service


async def require_manager_or_higher(
    actor=dep_actor,
) -> set[int] | None:
    if actor.role in (UserRole.admin, UserRole.manager):
        return actor
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
