import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from auto_parking.api.schemas.enterprise import EnterpriseFilter, EnterpriseOut
from auto_parking.db.models import Manager
from auto_parking.deps.commons import dep_actor
from auto_parking.deps.services import dep_enterprise_service, dep_manager_service

if TYPE_CHECKING:
    from auto_parking.service.enterprise import EnterpriseService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=list[EnterpriseOut])
async def get_enterprises(
    actor=dep_actor,
    manager_service=dep_manager_service,
    service: "EnterpriseService" = dep_enterprise_service,
):
    visible_ids = None
    logger.info(f"actor: {actor}")
    if actor.type == "manager":
        manager: Manager = await manager_service.get_by_id(actor.id)
        visible_ids = [enterprise.id for enterprise in manager.enterprises]

    return await service.get(EnterpriseFilter(ids=visible_ids))


@router.get("/{id}", response_model=EnterpriseOut)
async def get_enterprise(
    id: int,
    actor=dep_actor,
    manager_service=dep_manager_service,
    service: "EnterpriseService" = dep_enterprise_service,
):
    if actor.type == "manager":
        manager: Manager = await manager_service.get_by_id(actor.id)
        visible_ids = [e.id for e in manager.enterprises]
        if id not in visible_ids:
            raise HTTPException(status_code=404)

    return await service.get_by_id(id)
