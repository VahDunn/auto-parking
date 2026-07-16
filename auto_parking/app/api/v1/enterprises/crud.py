from typing import TYPE_CHECKING

from fastapi import APIRouter, status

from auto_parking.app.api.v1.enterprises.common import (
    dep_actor_guard,
    dep_visible_ids,
    enterprise_out,
)
from auto_parking.app.deps.services import dep_enterprise_service
from auto_parking.app.deps.visibility import ensure_enterprise_visible
from auto_parking.app.filter import EnterpriseFilter
from auto_parking.app.schemas.enterprise import EnterpriseOut

if TYPE_CHECKING:
    from auto_parking.app.service.enterprise import EnterpriseService

router = APIRouter()


@router.get("", response_model=list[EnterpriseOut])
async def get_enterprises(
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    ids = None if visible_enterprise_ids is None else list(visible_enterprise_ids)
    return [
        enterprise_out(enterprise) for enterprise in await service.get(EnterpriseFilter(ids=ids))
    ]


@router.get("/{id}", response_model=EnterpriseOut)
async def get_enterprise(
    id: int,
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    enterprise = await service.get_by_id(id)
    ensure_enterprise_visible(id, visible_enterprise_ids)
    return enterprise_out(enterprise)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enterprise(
    id: int,
    actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    ensure_enterprise_visible(id, visible_enterprise_ids)
    await service.delete(id, actor)
    return
