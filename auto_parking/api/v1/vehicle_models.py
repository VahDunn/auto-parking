import sqlalchemy as sa
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.deps import depends_db
from auto_parking.db.models import VehicleModel

router = APIRouter()


@router.get("")
async def get_vehicle_models(db: AsyncSession = depends_db):
    stmt = sa.select(VehicleModel)
    res = await db.execute(stmt)
    return res.scalars().all()
