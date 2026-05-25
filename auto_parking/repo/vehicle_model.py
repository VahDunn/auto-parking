from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.models import VehicleModel


class VehicleModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> Sequence[VehicleModel]:
        result = await self.db.execute(select(VehicleModel).order_by(VehicleModel.id))
        return result.scalars().all()

    async def get_by_id(self, model_id: int) -> VehicleModel | None:
        result = await self.db.execute(select(VehicleModel).where(VehicleModel.id == model_id))
        return result.scalar_one_or_none()
