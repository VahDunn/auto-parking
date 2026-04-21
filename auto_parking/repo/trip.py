from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.api.schemas.trip import TripFilter
from auto_parking.db.models import Enterprise, Trip, Vehicle, VehicleGpsPoint


class TripRepository:
    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db

    @staticmethod
    def _base_options():
        return (
            selectinload(Trip.vehicle).options(
                load_only(Vehicle.id, Vehicle.enterprise_id),
                selectinload(Vehicle.enterprise).options(
                    load_only(Enterprise.id, Enterprise.timezone)
                ),
            ),
            selectinload(Trip.start_point).options(
                load_only(
                    VehicleGpsPoint.id,
                    VehicleGpsPoint.vehicle_id,
                    VehicleGpsPoint.recorded_at_utc,
                    VehicleGpsPoint.position,
                )
            ),
            selectinload(Trip.end_point).options(
                load_only(
                    VehicleGpsPoint.id,
                    VehicleGpsPoint.vehicle_id,
                    VehicleGpsPoint.recorded_at_utc,
                    VehicleGpsPoint.position,
                )
            ),
        )

    async def get(self, filter_obj: TripFilter) -> Sequence[Trip]:
        stmt = select(Trip).options(*self._base_options())

        if filter_obj.vehicle_id is not None:
            stmt = stmt.where(Trip.vehicle_id == filter_obj.vehicle_id)

        if filter_obj.vehicle_ids:
            stmt = stmt.where(Trip.vehicle_id.in_(filter_obj.vehicle_ids))

        if filter_obj.started_from is not None:
            stmt = stmt.where(Trip.started_at_utc >= filter_obj.started_from)

        if filter_obj.started_to is not None:
            stmt = stmt.where(Trip.started_at_utc <= filter_obj.started_to)

        if filter_obj.ended_from is not None:
            stmt = stmt.where(Trip.ended_at_utc >= filter_obj.ended_from)

        if filter_obj.ended_to is not None:
            stmt = stmt.where(Trip.ended_at_utc <= filter_obj.ended_to)

        allowed_sort_fields = {
            "id": Trip.id,
            "vehicle_id": Trip.vehicle_id,
            "started_at_utc": Trip.started_at_utc,
            "ended_at_utc": Trip.ended_at_utc,
            "created_at": Trip.created_at,
        }

        if filter_obj.sort_by:
            raw_field = filter_obj.sort_by
            desc = raw_field.startswith("-")
            field_name = raw_field.lstrip("-")

            column = allowed_sort_fields.get(field_name)
            if column is not None:
                stmt = stmt.order_by(column.desc() if desc else column.asc())
            else:
                stmt = stmt.order_by(Trip.id)
        else:
            stmt = stmt.order_by(Trip.started_at_utc, Trip.id)

        stmt = stmt.offset(filter_obj.offset).limit(filter_obj.limit)

        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_by_id(self, trip_id: int) -> Trip | None:
        result = await self.db.execute(
            select(Trip).where(Trip.id == trip_id).options(*self._base_options())
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Trip:  # pyright: ignore[reportMissingTypeArgument]
        trip = Trip(**data)

        self.db.add(trip)
        await self.db.flush()
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(trip)
        return await self.get_by_id(trip.id)  # pyright: ignore[reportReturnType]

    async def update(self, trip_id: int, payload_dump: dict[str, Any]) -> Trip | None:
        trip = await self.get_by_id(trip_id)
        if not trip:
            return None

        for k, v in payload_dump.items():
            setattr(trip, k, v)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(trip)
        return await self.get_by_id(trip.id)

    async def delete(self, trip_id: int) -> bool:
        trip = await self.get_by_id(trip_id)
        if not trip:
            return False

        await self.db.delete(trip)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return True

    async def get_trips_inside_range(
        self,
        vehicle_id: int,
        date_from_utc: datetime,
        date_to_utc: datetime,
    ) -> Sequence[Trip]:
        stmt = (
            select(Trip)
            .where(Trip.vehicle_id == vehicle_id)
            .where(Trip.started_at_utc >= date_from_utc)
            .where(Trip.ended_at_utc <= date_to_utc)
            .options(*self._base_options())
            .order_by(Trip.started_at_utc.asc(), Trip.id.asc())
        )

        result = await self.db.execute(stmt)
        return result.unique().scalars().all()
