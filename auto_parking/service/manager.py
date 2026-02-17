from collections.abc import Sequence
from typing import TYPE_CHECKING

from auto_parking.db.models import Manager

if TYPE_CHECKING:
    from auto_parking.api.schemas.manager import ManagerFilter
    from auto_parking.repo.manager import ManagerRepository


class ManagerService:
    def __init__(self, repo: "ManagerRepository"):
        self._repo = repo

    async def get(self, filter_obj: "ManagerFilter | None" = None) -> Sequence["Manager"]:
        return await self._repo.get(filter_obj)

    async def get_by_id(self, id: int) -> "Manager | None":
        return await self._repo.get_by_id(id)
