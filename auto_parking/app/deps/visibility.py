from time import perf_counter

from fastapi import Depends, HTTPException, status

from auto_parking.app.deps.access import require_manager_or_higher
from auto_parking.app.deps.services import dep_user_service
from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.infrastructure.observability.performance import log_operation_stage

dep_require_manager_or_higher = Depends(require_manager_or_higher)


async def get_visible_enterprise_ids(
    actor=dep_require_manager_or_higher,
    user_service=dep_user_service,
) -> set[int] | None:
    started_at = perf_counter()
    if actor.role == UserRole.admin:
        log_operation_stage(
            operation="visible_enterprise_ids",
            stage="admin_short_circuit",
            duration_seconds=perf_counter() - started_at,
            actor_id=actor.id,
        )
        return None

    enterprise_ids = await user_service.get_visible_enterprise_ids(actor.id)
    if enterprise_ids is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    log_operation_stage(
        operation="visible_enterprise_ids",
        stage="manager_lookup",
        duration_seconds=perf_counter() - started_at,
        actor_id=actor.id,
        enterprise_count=len(enterprise_ids),
    )
    return enterprise_ids


def apply_enterprise_visibility(
    enterprise_ids: list[int] | None,
    visible_enterprise_ids: set[int] | None,
) -> list[int] | None:
    if visible_enterprise_ids is None:
        return enterprise_ids
    if enterprise_ids is None:
        return sorted(visible_enterprise_ids)
    return [
        enterprise_id
        for enterprise_id in enterprise_ids
        if enterprise_id in visible_enterprise_ids
    ]


def ensure_enterprise_visible(
    enterprise_id: int,
    visible_enterprise_ids: set[int] | None,
) -> None:
    if visible_enterprise_ids is not None and enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
