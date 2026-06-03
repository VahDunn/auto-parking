from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.models import VehicleModel
from auto_parking.filter import VehicleModelFilter


class VehicleModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: VehicleModelFilter) -> Sequence[VehicleModel]:
        stmt = select(VehicleModel)

        if filter_obj.ids:
            stmt = stmt.where(VehicleModel.id.in_(filter_obj.ids))

        if filter_obj.name:
            stmt = stmt.where(func.lower(VehicleModel.name) == filter_obj.name.casefold())

        result = await self.db.execute(stmt.order_by(VehicleModel.id))
        return result.scalars().all()

    async def get_all(self) -> Sequence[VehicleModel]:
        return await self.get(VehicleModelFilter())

    async def get_by_id(self, model_id: int) -> VehicleModel | None:
        models = await self.get(VehicleModelFilter(ids=[model_id]))
        return models[0] if models else None

    async def get_by_name(self, name: str) -> VehicleModel | None:
        models = await self.get(VehicleModelFilter(name=name))
        return models[0] if models else None
