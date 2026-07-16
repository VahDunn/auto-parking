import json
from collections.abc import Sequence
from time import perf_counter

from auto_parking.app.ports.cache import CacheClient
from auto_parking.core.domain.models import VehicleModelInfo
from auto_parking.infrastructure.db.models import VehicleModel
from auto_parking.infrastructure.db.repositories.vehicle_model import VehicleModelRepository
from auto_parking.infrastructure.observability.performance import log_cache_lookup


class VehicleModelService:
    def __init__(
        self,
        repo: VehicleModelRepository,
        cache: CacheClient | None = None,
        cache_ttl_seconds: int = 3600,
    ):
        self._repo = repo
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def get_all(self) -> list[VehicleModelInfo]:
        models: Sequence[VehicleModel] = await self._repo.get_all()
        return [self._build_model(model) for model in models]

    async def get_by_id(self, model_id: int) -> VehicleModelInfo | None:
        model = await self._repo.get_by_id(model_id)
        return self._build_model(model) if model is not None else None

    async def get_by_name(self, name: str) -> VehicleModelInfo | None:
        normalized_name = name.strip().casefold()
        if not normalized_name:
            return None

        cached = await self._get_cached_model(normalized_name)
        if cached is not None:
            return cached

        model = await self._repo.get_by_name(name.strip())
        if model is None:
            return None

        result = self._build_model(model)
        await self._cache_model(normalized_name, result)
        return result

    async def _get_cached_model(self, normalized_name: str) -> VehicleModelInfo | None:
        if self._cache is None:
            return None

        started_at = perf_counter()
        try:
            cached = await self._cache.get_text(self._cache_key(normalized_name))
            log_cache_lookup(
                operation="vehicle_model_by_name",
                result="hit" if cached is not None else "miss",
                duration_seconds=perf_counter() - started_at,
            )
            return VehicleModelInfo(**json.loads(cached)) if cached is not None else None
        except Exception:
            log_cache_lookup(
                operation="vehicle_model_by_name",
                result="error",
                duration_seconds=perf_counter() - started_at,
            )
            return None

    async def _cache_model(self, normalized_name: str, model: VehicleModelInfo) -> None:
        if self._cache is None:
            return

        try:
            await self._cache.set_text(
                self._cache_key(normalized_name),
                json.dumps(model.to_dict()),
                ttl_seconds=self._cache_ttl_seconds,
            )
        except Exception:
            return None

    @staticmethod
    def _cache_key(normalized_name: str) -> str:
        return f"vehicle-model:name:{normalized_name}"

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
