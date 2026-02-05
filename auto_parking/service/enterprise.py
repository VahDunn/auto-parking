from typing import TYPE_CHECKING

from auto_parking.api.schemas.enterprise import EnterpriseOut
from auto_parking.core.errors import NotFoundError
from auto_parking.repo.enterprise import EnterpriseRepository

if TYPE_CHECKING:
    from auto_parking.db.models import Enterprise


class EnterpriseService:
    def __init__(self, repo: EnterpriseRepository):
        self._repo = repo

    async def get_by_id(self, id: int) -> EnterpriseOut:
        enterprise = await self._repo.get_by_id(id)
        if enterprise is None:
            raise NotFoundError(f"Enterprise with id {id} not found")
        return self._build_out(enterprise)

    async def get(self) -> list[EnterpriseOut]:
        return [
            EnterpriseOut(
                id=enterprise.id,
                name=enterprise.name,
                settlement=enterprise.settlement,
                vehicles=[v.id for v in enterprise.vehicles],
                drivers=[d.id for d in enterprise.drivers],
            )
            for enterprise in await self._repo.get()
        ]

    @staticmethod
    def _build_out(enterprise: "Enterprise") -> EnterpriseOut:
        return EnterpriseOut(
            id=enterprise.id,
            name=enterprise.name,
            settlement=enterprise.settlement,
            vehicles=[v.id for v in enterprise.vehicles],
            drivers=[d.id for d in enterprise.drivers],
        )
