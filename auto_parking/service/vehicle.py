from typing import TYPE_CHECKING, Sequence

from auto_parking.api.schemas.vehicle import VehicleFilter, VehicleOut

if TYPE_CHECKING:
    from auto_parking.db.models import Vehicle
    from auto_parking.repo.vehicle import VehicleRepository
    from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleUpdate

class VehicleService:
    def __init__(self, repo: 'VehicleRepository') -> None:
        self._repo = repo

    async def get(self, filter: VehicleFilter) -> list[VehicleOut]:
        vehicles: Sequence['Vehicle'] = await self._repo.get(filter)
        return [VehicleOut.model_validate(v, from_attributes=True) for v in vehicles]

    async def get_by_id(self, id: int) -> VehicleOut | None:
        vehicle: 'Vehicle | None' = await self._repo.get_by_id(id)
        return VehicleOut.model_validate(vehicle, from_attributes=True) if vehicle else None

    async def create(self, vehicle_payload: 'VehicleCreate') -> VehicleOut:
        vehicle: 'Vehicle' = await self._repo.create(vehicle_payload.model_dump())
        return VehicleOut.model_validate(vehicle, from_attributes=True)

    async def update(self, id: int, payload: 'VehicleUpdate') -> VehicleOut | None:
        data = payload.model_dump(exclude_unset=True)
        vehicle = await self._repo.update(id, data)
        return VehicleOut.model_validate(vehicle, from_attributes=True) if vehicle else None

    async def delete(self, id: int) -> bool:
        return await self._repo.delete(id)
