from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.models import Manager

if TYPE_CHECKING:
    from auto_parking.api.schemas.manager import ManagerFilter


class ManagerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: "ManagerFilter | None" = None) -> Sequence[Manager]:
        stmt = select(Manager).order_by(Manager.id)
        if filter_obj:
            if filter_obj.ids:
                stmt = stmt.where(Manager.id.in_(filter_obj.ids))
            if filter_obj.username:
                stmt = stmt.where(Manager.username == filter_obj.username)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, manager_id: int) -> Manager | None:
        result = await self.db.execute(select(Manager).where(Manager.id == manager_id))
        return result.scalar_one_or_none()
