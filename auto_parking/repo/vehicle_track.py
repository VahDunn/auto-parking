from collections.abc import Sequence
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import Row, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.models import Trip, VehicleGpsPoint
from auto_parking.filter import VehicleTrackFilter


class VehicleTrackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, filter_obj: VehicleTrackFilter) -> Sequence[Row[Any]]:
        stmt = select(
            VehicleGpsPoint.id,
            VehicleGpsPoint.vehicle_id,
            VehicleGpsPoint.recorded_at_utc,
            func.ST_Y(VehicleGpsPoint.position).label("latitude"),
            func.ST_X(VehicleGpsPoint.position).label("longitude"),
        )

        if filter_obj.vehicle_id is not None:
            stmt = stmt.where(VehicleGpsPoint.vehicle_id == filter_obj.vehicle_id)
        if filter_obj.vehicle_ids:
            stmt = stmt.where(VehicleGpsPoint.vehicle_id.in_(filter_obj.vehicle_ids))
        if filter_obj.recorded_from is not None:
            stmt = stmt.where(VehicleGpsPoint.recorded_at_utc >= filter_obj.recorded_from)
        if filter_obj.recorded_to is not None:
            stmt = stmt.where(VehicleGpsPoint.recorded_at_utc <= filter_obj.recorded_to)
        if filter_obj.intervals is not None:
            if not filter_obj.intervals:
                return []
            stmt = stmt.where(
                or_(
                    *(
                        and_(
                            VehicleGpsPoint.recorded_at_utc >= started_at_utc,
                            VehicleGpsPoint.recorded_at_utc <= ended_at_utc,
                        )
                        for started_at_utc, ended_at_utc in filter_obj.intervals
                    )
                )
            )
        if filter_obj.trip_started_from is not None or filter_obj.trip_ended_to is not None:
            stmt = stmt.join(
                Trip,
                and_(
                    Trip.vehicle_id == VehicleGpsPoint.vehicle_id,
                    VehicleGpsPoint.recorded_at_utc >= Trip.started_at_utc,
                    VehicleGpsPoint.recorded_at_utc <= Trip.ended_at_utc,
                ),
            ).distinct()
            if filter_obj.trip_started_from is not None:
                stmt = stmt.where(Trip.started_at_utc >= filter_obj.trip_started_from)
            if filter_obj.trip_ended_to is not None:
                stmt = stmt.where(Trip.ended_at_utc <= filter_obj.trip_ended_to)

        result = await self.db.execute(
            stmt.order_by(
                VehicleGpsPoint.vehicle_id,
                VehicleGpsPoint.recorded_at_utc,
                VehicleGpsPoint.id,
            )
        )
        return result.all()

    async def create(self, data: dict[str, Any]) -> VehicleGpsPoint:
        point = self._make_point(data)
        self.db.add(point)
        await self.db.flush()

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(point)
        return point

    async def create_many(
        self,
        items: Sequence[dict[str, Any]],
    ) -> Sequence[VehicleGpsPoint]:
        if not items:
            return []

        points = [self._make_point(item) for item in items]
        self.db.add_all(points)
        await self.db.flush()

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return points

    @classmethod
    def _make_point(cls, data: dict[str, Any]) -> VehicleGpsPoint:
        return VehicleGpsPoint(
            vehicle_id=data["vehicle_id"],
            recorded_at_utc=data["recorded_at_utc"],
            position=cls._point_wkt(data["longitude"], data["latitude"]),
        )

    @staticmethod
    def _point_wkt(lon: float, lat: float) -> WKTElement:
        return WKTElement(f"POINT({lon} {lat})", srid=4326)
