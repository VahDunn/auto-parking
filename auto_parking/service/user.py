from collections.abc import Sequence
from typing import TYPE_CHECKING

from auto_parking.db.models import User

if TYPE_CHECKING:
    from auto_parking.filter import UserFilter
    from auto_parking.repo.user import UserRepository


class UserService:
    def __init__(self, repo: "UserRepository"):
        self._repo = repo

    async def get(self, filter_obj: "UserFilter | None" = None) -> Sequence["User"]:
        return await self._repo.get(filter_obj)

    async def get_by_id(self, id: int) -> "User | None":
        return await self._repo.get_by_id(id)
