import sqlalchemy as sa
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.schemas.vehicle import VehicleOut
from auto_parking.db.models import Vehicle
from auto_parking.deps.commons import depends_db

router = APIRouter()


@router.get("", response_model=list[VehicleOut])
async def get_vehicles(db: AsyncSession = depends_db):
    stmt = sa.select(Vehicle)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{id}", response_model=VehicleOut)
async def get_vehicle(id: int, db: AsyncSession = depends_db):
    stmt = sa.select(Vehicle).where(Vehicle.id == id)
    res = await db.execute(stmt)
    return res.scalar()
