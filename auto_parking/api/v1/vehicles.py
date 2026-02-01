import sqlalchemy as sa
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.deps import depends_db
from auto_parking.db.models import Vehicle

router = APIRouter()


@router.get("")
async def get_vehicles(db: AsyncSession = depends_db):
    stmt = sa.select(Vehicle)
    res = await db.execute(stmt)
    return res.scalars().all()
