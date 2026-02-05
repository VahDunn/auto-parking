from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.db.models import Driver, Vehicle


class DriverRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self) -> Sequence[Driver]:
        result = await self.db.execute(
            select(Driver).options(
                selectinload(Driver.vehicles).options(
                    load_only(Vehicle.id),
                ),
                selectinload(Driver.active_vehicle).options(
                    load_only(Vehicle.id),
                ),
            )
        )
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
