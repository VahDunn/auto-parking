from fastapi import APIRouter

from auto_parking.api.schemas.enterprise import EnterpriseOut
from auto_parking.deps import depends_enterprise_service
from auto_parking.service.enterprise import EnterpriseService

router = APIRouter()


@router.get(
    "",
    response_model=list[EnterpriseOut],
)
async def get_enterprises(
    service: EnterpriseService = depends_enterprise_service,
):
    return await service.get_enterprises()


@router.get(
    "/{id}",
    response_model=EnterpriseOut,
)
async def get_enterprise(
    id: int,
    service: EnterpriseService = depends_enterprise_service,
):
    return await service.get_enterprise_by_id(id)
