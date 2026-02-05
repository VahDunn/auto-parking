from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.db.models import Driver, Vehicle


class VehicleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self) -> Sequence[Vehicle]:
        result = await self.db.execute(
            select(Vehicle).options(
                selectinload(Vehicle.drivers).options(
                    load_only(Driver.id),
                ),
            )
        )
        return result.unique().scalars().all()

    async def get_by_id(self, vehicle_id: int) -> Vehicle | None:
        result = await self.db.execute(
            select(Vehicle)
            .where(Vehicle.id == vehicle_id)
            .options(
                selectinload(Vehicle.drivers).options(
                    load_only(Driver.id),
                ),
            )
        )
        return result.scalar_one_or_none()
