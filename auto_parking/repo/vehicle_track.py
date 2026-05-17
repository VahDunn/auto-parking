from collections.abc import Sequence
from datetime import datetime
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import Row, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.models import VehicleGpsPoint


class VehicleTrackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_points(
        self,
        vehicle_id: int,
        date_from_utc: datetime,
        date_to_utc: datetime,
    ) -> Sequence[Any]:
        stmt = (
            select(
                VehicleGpsPoint.recorded_at_utc,
                func.ST_Y(VehicleGpsPoint.position).label("latitude"),
                func.ST_X(VehicleGpsPoint.position).label("longitude"),
                func.ST_AsGeoJSON(VehicleGpsPoint.position).label("geojson"),
            )
            .where(VehicleGpsPoint.vehicle_id == vehicle_id)
            .where(VehicleGpsPoint.recorded_at_utc >= date_from_utc)
            .where(VehicleGpsPoint.recorded_at_utc <= date_to_utc)
            .order_by(VehicleGpsPoint.recorded_at_utc.asc())
        )

        result = await self.db.execute(stmt)
        return result.all()

    async def get_points_by_intervals(
        self,
        vehicle_id: int,
        intervals: Sequence[tuple[datetime, datetime]],
    ) -> Sequence[Row[Any]]:
        if not intervals:
            return []

        interval_conditions = [
            and_(
                VehicleGpsPoint.recorded_at_utc >= started_at_utc,
                VehicleGpsPoint.recorded_at_utc <= ended_at_utc,
            )
            for started_at_utc, ended_at_utc in intervals
        ]

        stmt = (
            select(
                VehicleGpsPoint.id,
                VehicleGpsPoint.recorded_at_utc,
                func.ST_Y(VehicleGpsPoint.position).label("latitude"),
                func.ST_X(VehicleGpsPoint.position).label("longitude"),
                func.ST_AsGeoJSON(VehicleGpsPoint.position).label("geojson"),
            )
            .where(VehicleGpsPoint.vehicle_id == vehicle_id)
            .where(or_(*interval_conditions))
            .order_by(VehicleGpsPoint.recorded_at_utc.asc())
        )

        result = await self.db.execute(stmt)
        return result.all()

    async def create_point(
        self,
        *,
        vehicle_id: int,
        recorded_at_utc: datetime,
        latitude: float,
        longitude: float,
    ) -> VehicleGpsPoint:
        point = VehicleGpsPoint(
            vehicle_id=vehicle_id,
            recorded_at_utc=recorded_at_utc,
            position=self._point_wkt(longitude, latitude),
        )

        self.db.add(point)
        await self.db.flush()

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(point)
        return point

    async def create_points_bulk(
            self,
            points_data: Sequence[dict[str, Any]],
    ) -> Sequence[VehicleGpsPoint]:
        if not points_data:
            return []
        points = [
            VehicleGpsPoint(
                vehicle_id=item["vehicle_id"],
                recorded_at_utc=item["recorded_at_utc"],
                position=self._point_wkt(
                    item["longitude"],
                    item["latitude"],
                ),
            )
            for item in points_data
        ]

        self.db.add_all(points)
        await self.db.flush()

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        for point in points:
            await self.db.refresh(point)

        return points

    @staticmethod
    def _point_wkt(lon: float, lat: float) -> WKTElement:
        return WKTElement(f"POINT({lon} {lat})", srid=4326)
