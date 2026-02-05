from collections.abc import Sequence

from auto_parking.api.schemas.driver import DriverOut
from auto_parking.db.models import Driver
from auto_parking.repo.driver import DriverRepository


class DriverService:
    def __init__(self, repo: DriverRepository):
        self.repo = repo

    async def get(self) -> list[DriverOut]:
        drivers: Sequence[Driver] = await self.repo.get()
        return [
            DriverOut(
                id=driver.id,
                name=driver.name,
                salary_rub=driver.salary_rub,
                enterprise_id=driver.enterprise_id,
                active_vehicle_id=driver.active_vehicle.id if driver.active_vehicle else None,
                vehicles=[v.id for v in driver.vehicles],
            )
            for driver in drivers
        ]

    async def get_by_id(self, id: int) -> DriverOut | None:
        driver = await self.repo.get_by_id(id)
        if not driver:
            return None
        return DriverOut(
            id=driver.id,
            name=driver.name,
            salary_rub=driver.salary_rub,
            enterprise_id=driver.enterprise_id,
            active_vehicle_id=driver.active_vehicle.id if driver.active_vehicle else None,
            vehicles=[v.id for v in driver.vehicles],
        )
