from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.db.models import Driver, Enterprise, Manager, Vehicle

if TYPE_CHECKING:
    from auto_parking.api.schemas.enterprise import EnterpriseFilter


class EnterpriseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: "EnterpriseFilter | None" = None) -> Sequence[Enterprise]:
        stmt = (
            select(Enterprise)
            .options(
                load_only(Enterprise.id, Enterprise.name, Enterprise.settlement),
                selectinload(Enterprise.vehicles).options(
                    load_only(Vehicle.id, Vehicle.enterprise_id, Vehicle.active_driver_id),
                    selectinload(Vehicle.drivers).options(
                        load_only(Driver.id),
                    ),
                ),
                selectinload(Enterprise.drivers).options(
                    load_only(Driver.id, Driver.enterprise_id),
                ),
                selectinload(Enterprise.managers).options(
                    load_only(Manager.id),
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
                load_only(Enterprise.id, Enterprise.name, Enterprise.settlement),
                selectinload(Enterprise.vehicles).options(
                    load_only(Vehicle.id, Vehicle.enterprise_id, Vehicle.active_driver_id),
                    selectinload(Vehicle.drivers).options(
                        load_only(Driver.id),
                    ),
                ),
                selectinload(Enterprise.drivers).options(
                    load_only(Driver.id, Driver.enterprise_id),
                ),
            )
        )
        return result.scalar_one_or_none()
