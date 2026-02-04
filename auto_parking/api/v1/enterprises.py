import sqlalchemy as sa
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.deps import depends_db
from auto_parking.api.schemas.enterprise import EnterpriseOut
from auto_parking.db.models import Enterprise

router = APIRouter()


@router.get("", response_model=list[EnterpriseOut])
async def get_enterprises(db: AsyncSession = depends_db):
    stmt = sa.select(Enterprise)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{id}", response_model=EnterpriseOut)
async def get_enterprise(id: int, db: AsyncSession = depends_db):
    stmt = sa.select(Enterprise).where(Enterprise.id == id)
    res = await db.execute(stmt)
    return res.scalar()
