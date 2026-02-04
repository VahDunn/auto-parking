from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auto_parking.db.models import Enterprise, Vehicle


class EnterpriseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_enterprises(self) -> Sequence[Enterprise]:
        res = await self.db.execute(select(Enterprise))
        return res.scalars().all()

    async def get_enterprise(self, enterprise_id: int) -> Enterprise | None:
        result = await self.db.execute(
            select(Enterprise)
            .where(Enterprise.id == enterprise_id)
            .options(
                selectinload(Enterprise.vehicles).options(
                    selectinload(Vehicle.drivers),
                    selectinload(Vehicle.active_driver),
                )
            )
        )
        return result.scalar_one_or_none()
