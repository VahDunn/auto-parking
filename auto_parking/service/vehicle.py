from auto_parking.api.schemas.vehicle import VehicleOut
from auto_parking.repo.vehicle import VehicleRepository


class VehicleService:
    def __init__(self, repo: VehicleRepository) -> None:
        self._repo = repo

    async def get(self) -> list[VehicleOut]:
        vehicles = await self._repo.get()
        return [
            VehicleOut(
                id=v.id,
                vehicle_number=v.vehicle_number,
                model_id=v.model_id,
                price=v.price,
                accident_number=v.accident_number,
                manufacture_year=v.manufacture_year,
                owners_count=v.owners_count,
                mileage=v.mileage,
                enterprise_id=v.enterprise_id,
                drivers=[d.id for d in v.drivers],
                active_driver_id=v.active_driver_id,
            )
            for v in vehicles
        ]

    async def get_by_id(self, id: int) -> VehicleOut | None:
        vehicle = await self._repo.get_by_id(id)
        if not vehicle:
            return None
        return VehicleOut(
            id=vehicle.id,
            vehicle_number=vehicle.vehicle_number,
            model_id=vehicle.model_id,
            price=vehicle.price,
            accident_number=vehicle.accident_number,
            manufacture_year=vehicle.manufacture_year,
            owners_count=vehicle.owners_count,
            mileage=vehicle.mileage,
            enterprise_id=vehicle.enterprise_id,
            drivers=[driver.id for driver in vehicle.drivers],
            active_driver_id=vehicle.active_driver_id,
        )
