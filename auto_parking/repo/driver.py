from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.api.schemas.driver import DriverFilter
from auto_parking.db.models import Driver, Vehicle


class DriverRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter: DriverFilter) -> Sequence[Driver]:
        stmt = select(Driver).options(
            selectinload(Driver.vehicles).options(
                load_only(Vehicle.id),
            ),
            selectinload(Driver.active_vehicle).options(
                load_only(Vehicle.id),
            ),
        )

        if filter:
            if filter.ids:
                stmt = stmt.where(Driver.id.in_(filter.ids))
            if filter.enterprise_id is not None:
                stmt = stmt.where(Driver.enterprise_id == filter.enterprise_id)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, driver_id: int) -> Driver | None:
        result = await self.db.execute(
            select(Driver)
            .where(Driver.id == driver_id)
            .options(
                selectinload(Driver.vehicles).options(
                    load_only(Vehicle.id),
                ),
                selectinload(Driver.active_vehicle).options(
                    load_only(Vehicle.id),
                ),
            )
        )
        return result.scalar_one_or_none()
