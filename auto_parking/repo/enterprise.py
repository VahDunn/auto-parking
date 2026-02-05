from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from auto_parking.db.models import Driver, Enterprise, Vehicle


class EnterpriseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self) -> Sequence[Enterprise]:
        result = await self.db.execute(
            select(Enterprise)
            .options(
                load_only(Enterprise.id, Enterprise.name, Enterprise.settlement),
                selectinload(Enterprise.vehicles).options(
                    load_only(Vehicle.id, Vehicle.enterprise_id, Vehicle.active_driver_id),
                    selectinload(Vehicle.drivers).options(
                        load_only(Driver.id),
                    ),
                ),
                selectinload(Enterprise.drivers).options(
                    load_only(Driver.id, Driver.enterprise_id),
                ),
            )
            .order_by(Enterprise.id)
        )
        return result.unique().scalars().all()

    async def get_by_id(self, enterprise_id: int) -> Enterprise | None:
        result = await self.db.execute(
            select(Enterprise)
            .where(Enterprise.id == enterprise_id)
            .options(
                load_only(Enterprise.id, Enterprise.name, Enterprise.settlement),
                selectinload(Enterprise.vehicles).options(
                    load_only(Vehicle.id, Vehicle.enterprise_id, Vehicle.active_driver_id),
                    selectinload(Vehicle.drivers).options(
                        load_only(Driver.id),
                    ),
                ),
                selectinload(Enterprise.drivers).options(
                    load_only(Driver.id, Driver.enterprise_id),
                ),
            )
        )
        return result.scalar_one_or_none()
