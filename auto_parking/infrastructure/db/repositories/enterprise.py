from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, noload, selectinload

from auto_parking.infrastructure.db.models import Driver, Enterprise, User, Vehicle

if TYPE_CHECKING:
    from auto_parking.app.filter import EnterpriseFilter


class EnterpriseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _relation_options():
        return (
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

    @staticmethod
    def _without_relations_options():
        return (
            noload(Enterprise.vehicles),
            noload(Enterprise.drivers),
            noload(Enterprise.users),
        )

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
            )
            .order_by(Enterprise.id)
        )

        relation_options = (
            self._relation_options()
            if filter_obj is None or filter_obj.load_relations
            else self._without_relations_options()
        )
        stmt = stmt.options(*relation_options)

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
                *self._relation_options(),
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
