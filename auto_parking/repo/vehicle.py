from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.db.models import Driver, Enterprise, Vehicle
from auto_parking.filter import VehicleFilter


class VehicleRepository:
    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db

    @staticmethod
    def _base_options():
        return (
            selectinload(Vehicle.drivers).options(load_only(Driver.id)),
            selectinload(Vehicle.enterprise).options(load_only(Enterprise.id, Enterprise.timezone)),
        )

    async def get(self, filter_obj: VehicleFilter) -> Sequence[Vehicle]:
        stmt = select(Vehicle).options(*self._base_options())

        if filter_obj.id:
            stmt = stmt.where(Vehicle.id.in_(filter_obj.id))

        if filter_obj.enterprise_ids:
            stmt = stmt.where(Vehicle.enterprise_id.in_(filter_obj.enterprise_ids))

        if filter_obj.driver_id is not None:
            stmt = stmt.where(Vehicle.drivers.any(Driver.id == filter_obj.driver_id))

        allowed_sort_fields = {
            "id": Vehicle.id,
            "price": Vehicle.price,
            "mileage": Vehicle.mileage,
            "vehicle_number": Vehicle.vehicle_number,
            "owners_count": Vehicle.owners_count,
            "accident_number": Vehicle.accident_number,
            "manufacture_year": Vehicle.manufacture_year,
            "model_id": Vehicle.model_id,
            "enterprise_id": Vehicle.enterprise_id,
            "active_driver_id": Vehicle.active_driver_id,
            "color": Vehicle.color,
        }

        if filter_obj.sort_by:
            raw_field = filter_obj.sort_by
            desc = raw_field.startswith("-")
            field_name = raw_field.lstrip("-")

            column = allowed_sort_fields.get(field_name)
            if column is not None:
                stmt = stmt.order_by(column.desc() if desc else column.asc())
            else:
                stmt = stmt.order_by(Vehicle.id)
        else:
            stmt = stmt.order_by(Vehicle.id)

        if filter_obj.offset is not None:
            stmt = stmt.offset(filter_obj.offset)

        if filter_obj.limit is not None:
            stmt = stmt.limit(filter_obj.limit)

        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, vehicle_id: int) -> Vehicle | None:
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id).options(*self._base_options())
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
        return await self.get_by_id(vehicle.id)  # pyright: ignore[reportReturnType]

    async def update(self, vehicle_id: int, data: dict) -> Vehicle | None:  # pyright: ignore[reportMissingTypeArgument]
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
