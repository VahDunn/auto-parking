from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, load_only, noload, selectinload

from auto_parking.app.filter import VehicleFilter
from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.infrastructure.db.models import Driver, Enterprise, User, Vehicle, user_enterprise


class VehicleRepository:
    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db

    @staticmethod
    def _base_options():
        return (
            noload(Vehicle.model),
            noload(Vehicle.active_driver),
            selectinload(Vehicle.drivers).options(
                load_only(Driver.id),
                noload(Driver.enterprise),
                noload(Driver.active_vehicle),
                noload(Driver.vehicles),
            ),
            joinedload(Vehicle.enterprise).options(
                load_only(Enterprise.id, Enterprise.timezone),
                noload(Enterprise.vehicles),
                noload(Enterprise.drivers),
                noload(Enterprise.users),
            ),
        )

    async def get(self, filter_obj: VehicleFilter) -> Sequence[Vehicle]:
        relation_options = (
            self._base_options()
            if filter_obj.load_relations
            else (
                noload(Vehicle.model),
                noload(Vehicle.active_driver),
                noload(Vehicle.drivers),
                noload(Vehicle.enterprise),
            )
        )
        stmt = select(Vehicle).options(*relation_options)

        if filter_obj.id:
            stmt = stmt.where(Vehicle.id.in_(filter_obj.id))

        if filter_obj.vehicle_number_prefix:
            vehicle_number_prefix = filter_obj.vehicle_number_prefix.strip().upper()
            stmt = stmt.where(Vehicle.vehicle_number.like(f"{vehicle_number_prefix}%"))

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

    async def manager_ids_for_enterprise(self, enterprise_id: int) -> list[int]:
        result = await self.db.execute(
            select(User.id)
            .join(user_enterprise, user_enterprise.c.user_id == User.id)
            .where(
                user_enterprise.c.enterprise_id == enterprise_id,
                User.role == UserRole.manager,
            )
            .order_by(User.id)
        )
        return [int(user_id) for user_id in result.scalars().all()]

    async def create(self, data: dict) -> Vehicle:
        vehicle = await self.create_uncommitted(data)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return await self.get_by_id(vehicle.id)  # pyright: ignore[reportReturnType]

    async def create_uncommitted(self, data: dict) -> Vehicle:
        vehicle = Vehicle(**data)
        self.db.add(vehicle)
        await self.db.flush()
        return await self.get_by_id(vehicle.id)  # pyright: ignore[reportReturnType]

    async def update(self, vehicle_id: int, data: dict) -> Vehicle | None:  # pyright: ignore[reportMissingTypeArgument]
        vehicle = await self.update_uncommitted(vehicle_id, data)
        if vehicle is None:
            return None

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return await self.get_by_id(vehicle.id)

    async def update_uncommitted(self, vehicle_id: int, data: dict) -> Vehicle | None:  # pyright: ignore[reportMissingTypeArgument]
        vehicle = await self.get_by_id(vehicle_id)
        if not vehicle:
            return None

        for k, v in data.items():
            setattr(vehicle, k, v)

        await self.db.flush()
        return await self.get_by_id(vehicle.id)

    async def delete(self, vehicle_id: int) -> bool:
        deleted = await self.delete_uncommitted(vehicle_id)
        if not deleted:
            return False

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return True

    async def delete_uncommitted(self, vehicle_id: int) -> bool:
        vehicle = await self.get_by_id(vehicle_id)
        if not vehicle:
            return False

        await self.db.delete(vehicle)
        await self.db.flush()

        return True
