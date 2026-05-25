from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.db.models import Driver, Enterprise, User, Vehicle

if TYPE_CHECKING:
    from auto_parking.filter import EnterpriseFilter


class EnterpriseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(
        self,
        filter_obj: "EnterpriseFilter | None" = None,
    ) -> Sequence[Enterprise]:
        stmt = (
            select(Enterprise)
            .options(
                load_only(
                    Enterprise.id,
                    Enterprise.name,
                    Enterprise.settlement,
                    Enterprise.timezone,
                ),
                selectinload(Enterprise.vehicles).options(
                    load_only(Vehicle.id, Vehicle.enterprise_id, Vehicle.active_driver_id),
                    selectinload(Vehicle.drivers).options(
                        load_only(Driver.id),
                    ),
                ),
                selectinload(Enterprise.drivers).options(
                    load_only(Driver.id, Driver.enterprise_id),
                ),
                selectinload(Enterprise.users).options(
                    load_only(User.id, User.role),
                ),
            )
            .order_by(Enterprise.id)
        )

        if filter_obj is not None and filter_obj.ids is not None:
            stmt = stmt.where(Enterprise.id.in_(filter_obj.ids))

        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, enterprise_id: int) -> Enterprise | None:
        result = await self.db.execute(
            select(Enterprise)
            .where(Enterprise.id == enterprise_id)
            .options(
                load_only(
                    Enterprise.id,
                    Enterprise.name,
                    Enterprise.settlement,
                    Enterprise.timezone,
                ),
                selectinload(Enterprise.vehicles).options(
                    load_only(Vehicle.id, Vehicle.enterprise_id, Vehicle.active_driver_id),
                    selectinload(Vehicle.drivers).options(
                        load_only(Driver.id),
                    ),
                ),
                selectinload(Enterprise.drivers).options(
                    load_only(Driver.id, Driver.enterprise_id),
                ),
                selectinload(Enterprise.users).options(
                    load_only(User.id, User.role),
                ),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Enterprise:  # pyright: ignore[reportMissingTypeArgument]
        enterprise = Enterprise(**data)

        self.db.add(enterprise)
        await self.db.flush()

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(enterprise)
        return enterprise

    async def delete(self, enterprise_id: int) -> bool:
        stmt = delete(Enterprise).where(Enterprise.id == enterprise_id).returning(Enterprise.id)
        res = await self.db.execute(stmt)
        deleted_id = res.scalar_one_or_none()
        if deleted_id is None:
            return False
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return True

    async def is_user_linked(self, enterprise_id: int, user_id: int) -> bool:
        stmt = (
            select(User.id)
            .select_from(Enterprise)
            .join(Enterprise.users)
            .where(Enterprise.id == enterprise_id, User.id == user_id)
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def count_enterprise_managers(self, enterprise_id: int) -> int:
        stmt = (
            select(func.count(User.id))
            .select_from(Enterprise)
            .join(Enterprise.users)
            .where(Enterprise.id == enterprise_id, User.role == UserRole.manager)
        )
        res = await self.db.execute(stmt)
        return int(res.scalar_one())
