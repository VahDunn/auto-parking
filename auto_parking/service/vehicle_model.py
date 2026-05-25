from collections.abc import Sequence

from auto_parking.core.models import VehicleModelInfo
from auto_parking.db.models import VehicleModel
from auto_parking.repo.vehicle_model import VehicleModelRepository


class VehicleModelService:
    def __init__(self, repo: VehicleModelRepository):
        self._repo = repo

    async def get_all(self) -> list[VehicleModelInfo]:
        models: Sequence[VehicleModel] = await self._repo.get_all()
        return [self._build_model(model) for model in models]

    async def get_by_id(self, model_id: int) -> VehicleModelInfo | None:
        model = await self._repo.get_by_id(model_id)
        return self._build_model(model) if model is not None else None

    @staticmethod
    def _build_model(model: VehicleModel) -> VehicleModelInfo:
        return VehicleModelInfo(
            id=model.id,
            name=model.name,
            type=model.type,
            horse_powers=model.horse_powers,
            seats_number=model.seats_number,
            fuel_capacity_liters=model.fuel_capacity_liters,
        )
