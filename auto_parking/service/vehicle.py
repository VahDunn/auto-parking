from collections.abc import Sequence
from typing import TYPE_CHECKING

from auto_parking.api.schemas.vehicle import VehicleOut
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc
from auto_parking.filter import VehicleFilter

if TYPE_CHECKING:
    from auto_parking.api.schemas.vehicle import VehicleCreate, VehicleUpdate
    from auto_parking.db.models import Vehicle
    from auto_parking.repo.vehicle import VehicleRepository


class VehicleService:
    def __init__(self, repo: "VehicleRepository") -> None:
        self._repo = repo

    async def get(self, filter_obj: VehicleFilter) -> list[VehicleOut]:
        vehicles: Sequence[Vehicle] = await self._repo.get(filter_obj)
        return [self._build_out(v) for v in vehicles]

    async def get_by_id(self, id: int) -> VehicleOut | None:
        vehicle: Vehicle | None = await self._repo.get_by_id(id)
        return self._build_out(vehicle) if vehicle else None

    async def create(self, vehicle_payload: "VehicleCreate") -> VehicleOut:
        data = vehicle_payload.model_dump()
        purchased_at = data.pop("purchased_at")
        data["purchased_at_utc"] = to_utc(purchased_at)

        vehicle: Vehicle = await self._repo.create(data)
        return self._build_out(vehicle)

    async def update(self, id: int, payload: "VehicleUpdate") -> VehicleOut | None:
        data = payload.model_dump(exclude_unset=True)

        if "purchased_at" in data:
            data["purchased_at_utc"] = to_utc(data.pop("purchased_at"))

        vehicle = await self._repo.update(id, data)
        return self._build_out(vehicle) if vehicle else None

    async def delete(self, id: int) -> bool:
        return await self._repo.delete(id)

    def _build_out(self, vehicle: "Vehicle") -> VehicleOut:
        enterprise = vehicle.enterprise
        tz = enterprise.timezone if enterprise else None

        purchased_at_utc = vehicle.purchased_at_utc

        return VehicleOut(
            id=vehicle.id,
            price=vehicle.price,
            mileage=vehicle.mileage,
            vehicle_number=vehicle.vehicle_number,
            owners_count=vehicle.owners_count,
            accident_number=vehicle.accident_number,
            manufacture_year=vehicle.manufacture_year,
            model_id=vehicle.model_id,
            color=vehicle.color,
            enterprise_id=vehicle.enterprise_id,
            drivers=[d.id for d in vehicle.drivers],
            active_driver_id=vehicle.active_driver_id or -1,
            purchased_at_utc=purchased_at_utc,
            purchased_at_enterprise=(
                to_enterprise_tz(purchased_at_utc, tz) if purchased_at_utc else None
            ),
            enterprise_timezone=tz or "UTC",
        )
