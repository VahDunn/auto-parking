from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.core.domain.enums import UserRole
from auto_parking.db.models import Enterprise, User

if TYPE_CHECKING:
    from auto_parking.filter import UserFilter


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: "UserFilter | None" = None) -> Sequence[User]:
        stmt = select(User).order_by(User.id)
        if filter_obj:
            if filter_obj.ids:
                stmt = stmt.where(User.id.in_(filter_obj.ids))
            if filter_obj.username:
                stmt = stmt.where(User.username == filter_obj.username)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, manager_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == manager_id))
        return result.scalar_one_or_none()

    async def get_notification_recipient_ids_by_enterprise(
        self,
        enterprise_id: int,
    ) -> list[int]:
        result = await self.db.execute(
            select(User.id)
            .outerjoin(User.enterprises)
            .where(
                (User.role == UserRole.admin)
                | (
                    (User.role == UserRole.manager)
                    & (Enterprise.id == enterprise_id)
                ),
            )
            .distinct()
            .order_by(User.id)
        )
        return list(result.scalars().all())
