from typing import TYPE_CHECKING

from auto_parking.app.filter import EnterpriseFilter
from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.core.domain.models import EnterpriseModel
from auto_parking.core.errors import ConflictError, ForbiddenError, NotFoundError

if TYPE_CHECKING:
    from auto_parking.infrastructure.db.models import Enterprise
    from auto_parking.infrastructure.db.repositories.enterprise import EnterpriseRepository


class EnterpriseService:
    def __init__(self, repo: "EnterpriseRepository"):
        self._repo = repo

    async def get_by_id(self, id: int) -> EnterpriseModel:
        enterprise = await self._repo.get_by_id(id)
        if enterprise is None:
            raise NotFoundError(f"Enterprise with id {id} not found")
        return self._build_out(enterprise)

    async def get(self, filter_obj: EnterpriseFilter) -> list[EnterpriseModel]:
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

        linked = any(user.id == actor.id for user in enterprise.users)
        if not linked:
            raise ForbiddenError("Forbidden")

        managers_count = self._count_managers(enterprise)
        if managers_count > 1:
            raise ConflictError("Enterprise is visible to other managers")

        ok = await self._repo.delete(enterprise_id)
        if not ok:
            raise NotFoundError("Enterprise not found")

    @staticmethod
    def _build_out(enterprise: "Enterprise") -> EnterpriseModel:
        managers = [u.id for u in enterprise.users if getattr(u, "role", None) == UserRole.manager]

        return EnterpriseModel(
            id=enterprise.id,
            name=enterprise.name,
            settlement=enterprise.settlement,
            vehicles=[v.id for v in enterprise.vehicles],
            drivers=[d.id for d in enterprise.drivers],
            managers=managers,
            timezone=enterprise.timezone,
        )

    @staticmethod
    def _count_managers(enterprise: "Enterprise") -> int:
        return sum(
            1 for user in enterprise.users if getattr(user, "role", None) == UserRole.manager
        )
