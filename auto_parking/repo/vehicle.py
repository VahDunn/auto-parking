from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.api.schemas.vehicle import VehicleFilter
from auto_parking.db.models import Driver, Vehicle


class VehicleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: VehicleFilter) -> Sequence[Vehicle]:
        stmt = (
            select(Vehicle)
            .options(
                selectinload(Vehicle.drivers).options(load_only(Driver.id)),
            )
            .order_by(Vehicle.id)
        )

        if filter_obj.id:
            stmt = stmt.where(Vehicle.id.in_(filter_obj.id))
        if filter_obj.enterprise_ids:
            stmt = stmt.where(Vehicle.enterprise_id.in_(filter_obj.enterprise_ids))
        if filter_obj.driver_id is not None:
            stmt = stmt.where(Vehicle.drivers.any(Driver.id == filter_obj.driver_id))

        stmt = stmt.offset(filter_obj.offset).limit(filter_obj.limit)

        result = await self.db.execute(stmt)
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

    async def create(self, data: dict) -> Vehicle:
        vehicle = Vehicle(**data)

        self.db.add(vehicle)
        await self.db.flush()
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(vehicle)
        return await self.get_by_id(vehicle.id)  # type: ignore[return-value]

    async def update(self, vehicle_id: int, data: dict) -> Vehicle | None:
        vehicle = await self.get_by_id(vehicle_id)
        if not vehicle:
            return None

        for k, v in data.items():
            setattr(vehicle, k, v)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(vehicle)
        return vehicle

    async def delete(self, vehicle_id: int) -> bool:
        vehicle = await self.get_by_id(vehicle_id)
        if not vehicle:
            return False

        await self.db.delete(vehicle)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return True
