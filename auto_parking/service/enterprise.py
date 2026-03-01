from typing import TYPE_CHECKING

from auto_parking.api.schemas.enterprise import EnterpriseFilter, EnterpriseOut
from auto_parking.core.domain.user_role import UserRole
from auto_parking.core.errors import ConflictError, ForbiddenError, NotFoundError

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
        enterprises = await self._repo.get(filter_obj)
        return [self._build_out(e) for e in enterprises]

    async def delete(self, enterprise_id: int, actor) -> None:
        enterprise = await self._repo.get_by_id(enterprise_id)
        if enterprise is None:
            raise NotFoundError("Enterprise not found")

        if actor.role == UserRole.admin:
            ok = await self._repo.delete(enterprise_id)
            if not ok:
                raise NotFoundError("Enterprise not found")
            return

        if actor.role != UserRole.manager:
            raise ForbiddenError("Forbidden")

        linked = await self._repo.is_user_linked(enterprise_id=enterprise_id, user_id=actor.id)
        if not linked:
            raise ForbiddenError("Forbidden")

        managers_count = await self._repo.count_enterprise_managers(enterprise_id)
        if managers_count > 1:
            raise ConflictError("Enterprise is visible to other managers")

        ok = await self._repo.delete(enterprise_id)
        if not ok:
            raise NotFoundError("Enterprise not found")

    @staticmethod
    def _build_out(enterprise: "Enterprise") -> EnterpriseOut:
        managers = [u.id for u in enterprise.users if getattr(u, "role", None) == UserRole.manager]

        return EnterpriseOut(
            id=enterprise.id,
            name=enterprise.name,
            settlement=enterprise.settlement,
            vehicles=[v.id for v in enterprise.vehicles],
            drivers=[d.id for d in enterprise.drivers],
            managers=managers,
        )
