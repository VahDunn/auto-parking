from fastapi import Depends, HTTPException, status

from auto_parking.core.enums.user_role import UserRole
from auto_parking.db.models import User
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import dep_user_service

dep_require_manager_or_higher = Depends(require_manager_or_higher)


async def get_visible_enterprise_ids(
    actor=dep_require_manager_or_higher,
    user_service=dep_user_service,
) -> set[int] | None:
    if actor.role == UserRole.admin:
        return None

    user: User | None = await user_service.get_by_id(actor.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {e.id for e in user.enterprises}
