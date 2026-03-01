import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from auto_parking.api.schemas.enterprise import EnterpriseFilter, EnterpriseOut
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import dep_enterprise_service
from auto_parking.deps.visibility import get_visible_enterprise_ids

if TYPE_CHECKING:
    from auto_parking.service.enterprise import EnterpriseService

router = APIRouter()
logger = logging.getLogger(__name__)


dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


@router.get("", response_model=list[EnterpriseOut])
async def get_enterprises(
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    ids = None if visible_enterprise_ids is None else list(visible_enterprise_ids)
    return await service.get(EnterpriseFilter(ids=ids))


@router.get("/{id}", response_model=EnterpriseOut)
async def get_enterprise(
    id: int,
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    enterprise = await service.get_by_id(id)
    if visible_enterprise_ids is not None and id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return enterprise


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enterprise(
    id: int,
    actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    if visible_enterprise_ids is not None and id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    await service.delete(id, actor)
    return
