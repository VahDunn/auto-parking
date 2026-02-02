import sqlalchemy as sa
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.deps import depends_db
from auto_parking.db.models import Vehicle, VehicleModel

router = APIRouter()


@router.get("")
async def get_vehicle_models(db: AsyncSession = depends_db):
    stmt = sa.select(VehicleModel)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{id}")
async def get_vehicle_model(id: int, db: AsyncSession = depends_db):
    stmt = sa.select(VehicleModel).where(Vehicle.id == id)
    res = await db.execute(stmt)
    return res.scalar()
