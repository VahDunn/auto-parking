from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from auto_parking.infrastructure.db.models import Enterprise, User, user_enterprise

if TYPE_CHECKING:
    from auto_parking.app.filter import UserFilter


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: "UserFilter | None" = None) -> Sequence[User]:
        stmt = select(User).order_by(User.id)
        if filter_obj:
            if not filter_obj.load_relations:
                stmt = stmt.options(noload(User.enterprises))
            if filter_obj.enterprise_id is not None:
                stmt = stmt.join(User.enterprises).where(Enterprise.id == filter_obj.enterprise_id)
            if filter_obj.ids:
                stmt = stmt.where(User.id.in_(filter_obj.ids))
            if filter_obj.username:
                stmt = stmt.where(User.username == filter_obj.username)
            if filter_obj.role is not None:
                stmt = stmt.where(User.role == filter_obj.role)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, manager_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == manager_id))
        return result.scalar_one_or_none()

    async def get_visible_enterprise_ids(self, user_id: int) -> set[int] | None:
        stmt = (
            select(user_enterprise.c.enterprise_id)
            .select_from(User)
            .outerjoin(user_enterprise, User.id == user_enterprise.c.user_id)
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        enterprise_ids = result.scalars().all()
        if not enterprise_ids:
            return None
        return {enterprise_id for enterprise_id in enterprise_ids if enterprise_id is not None}
