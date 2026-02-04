import sqlalchemy as sa
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.schemas.driver import DriverOut
from auto_parking.db.models import Driver
from auto_parking.deps.commons import depends_db

router = APIRouter()


@router.get("", response_model=list[DriverOut])
async def get_drivers(db: AsyncSession = depends_db):
    stmt = sa.select(Driver)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{id}", response_model=DriverOut)
async def get_driver(id: int, db: AsyncSession = depends_db):
    stmt = sa.select(Driver).where(Driver.id == id)
    res = await db.execute(stmt)
    return res.scalar()
