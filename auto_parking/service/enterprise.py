from typing import TYPE_CHECKING

from auto_parking.api.schemas.driver import DriverShort
from auto_parking.api.schemas.enterprise import EnterpriseOut
from auto_parking.api.schemas.vehicle import VehicleShort
from auto_parking.core.errors import NotFoundError
from auto_parking.repo.enterprise import EnterpriseRepository

if TYPE_CHECKING:
    from auto_parking.db.models import Enterprise


class EnterpriseService:
    def __init__(self, repo: EnterpriseRepository):
        self._repo = repo

    async def get_enterprise_by_id(self, id: int) -> EnterpriseOut:
        enterprise = await self._repo.get_enterprise(id)
        if enterprise is None:
            raise NotFoundError(f"Enterprise with id {id} not found")
        return self._build_enterprise_out(enterprise)

    async def get_enterprises(self) -> list[EnterpriseOut]:
        return [
            EnterpriseOut(
                id=enterprise.id,
                name=enterprise.name,
                settlement=enterprise.settlement,
            )
            for enterprise in await self._repo.get_enterprises()
        ]

    @staticmethod
    def _build_enterprise_out(enterprise: "Enterprise"):
        return EnterpriseOut(
            id=enterprise.id,
            name=enterprise.name,
            settlement=enterprise.settlement,
            vehicles=[
                VehicleShort(
                    id=vehicle.id,
                    vehicle_number=vehicle.vehicle_number,
                    model_id=vehicle.model_id,
                    drivers=[
                        DriverShort(
                            id=driver.id,
                            name=driver.name,
                            enterprise_id=driver.enterprise_id,
                        )
                        for driver in vehicle.drivers
                    ],
                    active_driver=(
                        DriverShort(
                            id=vehicle.active_driver.id,
                            name=vehicle.active_driver.name,
                            enterprise_id=vehicle.active_driver.enterprise_id,
                        )
                        if vehicle.active_driver
                        else None
                    ),
                )
                for vehicle in enterprise.vehicles
            ],
        )
