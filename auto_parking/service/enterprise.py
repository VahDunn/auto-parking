from typing import TYPE_CHECKING

from auto_parking.api.schemas.enterprise import EnterpriseFilter, EnterpriseOut
from auto_parking.core.errors import NotFoundError

if TYPE_CHECKING:
    from auto_parking.db.models import Enterprise
    from auto_parking.repo.enterprise import EnterpriseRepository


class EnterpriseService:
    def __init__(self, repo: "EnterpriseRepository"):
        self._repo = repo

    async def get_by_id(self, id: int) -> EnterpriseOut:
        enterprise = await self._repo.get_by_id(id)
        if enterprise is None:
            raise NotFoundError(f"Enterprise with id {id} not found")
        return self._build_out(enterprise)

    async def get(self, filter_obj: EnterpriseFilter) -> list[EnterpriseOut]:
        return [self._build_out(enterprise) for enterprise in await self._repo.get(filter_obj)]

    @staticmethod
    def _build_out(enterprise: "Enterprise") -> EnterpriseOut:
        return EnterpriseOut(
            id=enterprise.id,
            name=enterprise.name,
            settlement=enterprise.settlement,
            vehicles=[v.id for v in enterprise.vehicles],
            drivers=[d.id for d in enterprise.drivers],
            managers=[m.id for m in enterprise.managers],
        )
