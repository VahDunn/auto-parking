from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
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
    ) -> Sequence:
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
