import json
import logging
from collections.abc import Sequence
from datetime import datetime
from time import perf_counter
from typing import TYPE_CHECKING

from auto_parking.app.filter import VehicleFilter
from auto_parking.app.ports.cache import CacheClient
from auto_parking.app.ports.events import (
    AUDIT_EVENTS_TOPIC,
    VEHICLE_EVENTS_TOPIC,
    EventEnvelope,
    EventProducer,
)
from auto_parking.core.domain.models import VehicleModel
from auto_parking.infrastructure.observability.performance import log_cache_lookup

if TYPE_CHECKING:
    from auto_parking.infrastructure.db.models import Vehicle
    from auto_parking.infrastructure.db.repositories.outbox import OutboxRepository
    from auto_parking.infrastructure.db.repositories.vehicle import VehicleRepository

logger = logging.getLogger(__name__)


class VehicleService:
    def __init__(
        self,
        repo: "VehicleRepository",
        cache: CacheClient | None = None,
        cache_ttl_seconds: int = 300,
        event_producer: EventProducer | None = None,
        outbox_repo: "OutboxRepository | None" = None,
        event_topic: str = VEHICLE_EVENTS_TOPIC,
        audit_event_topic: str = AUDIT_EVENTS_TOPIC,
    ) -> None:
        self._repo = repo
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._event_producer = event_producer
        self._outbox_repo = outbox_repo
        self._event_topic = event_topic
        self._audit_event_topic = audit_event_topic

    async def get(self, filter_obj: VehicleFilter) -> list[VehicleModel]:
        vehicles: Sequence[Vehicle] = await self._repo.get(filter_obj)
        return [self._build_out(v) for v in vehicles]

    async def get_by_id(self, id: int) -> VehicleModel | None:
        cached = await self._get_cached_vehicle(id)
        if cached is not None:
            return cached

        vehicle: Vehicle | None = await self._repo.get_by_id(id)
        if vehicle is None:
            return None

        result = self._build_out(vehicle)
        await self._cache_vehicle(result)
        return result

    async def create(self, vehicle: VehicleModel) -> VehicleModel:
        data = self._persistence_data(vehicle)
        if self._outbox_repo is not None:
            try:
                vehicle = await self._repo.create_uncommitted(data)
                result = self._build_out(vehicle)
                await self._emit_vehicle_event("vehicle.created", result)
                await self._repo.db.commit()
            except Exception:
                await self._repo.db.rollback()
                raise

            await self._cache_vehicle(result)
            return result

        vehicle: Vehicle = await self._repo.create(data)
        result = self._build_out(vehicle)
        await self._cache_vehicle(result)
        await self._emit_vehicle_event("vehicle.created", result)
        return result

    async def update(self, id: int, vehicle: VehicleModel) -> VehicleModel | None:
        data = self._persistence_data(vehicle)
        if self._outbox_repo is not None:
            try:
                vehicle = await self._repo.update_uncommitted(id, data)
                if vehicle is None:
                    await self._repo.db.rollback()
                    return None

                result = self._build_out(vehicle)
                await self._emit_vehicle_event("vehicle.updated", result)
                await self._repo.db.commit()
            except Exception:
                await self._repo.db.rollback()
                raise

            await self._cache_vehicle(result)
            return result

        vehicle = await self._repo.update(id, data)
        if vehicle is None:
            return None

        result = self._build_out(vehicle)
        await self._cache_vehicle(result)
        await self._emit_vehicle_event("vehicle.updated", result)
        return result

    async def delete(self, id: int) -> bool:
        current = await self.get_by_id(id)
        if self._outbox_repo is not None:
            try:
                deleted = await self._repo.delete_uncommitted(id)
                if deleted:
                    await self._emit_vehicle_event("vehicle.deleted", current, vehicle_id=id)
                await self._repo.db.commit()
            except Exception:
                await self._repo.db.rollback()
                raise

            if deleted:
                await self._delete_cached_vehicle(id)
            return deleted

        deleted = await self._repo.delete(id)
        if deleted:
            await self._delete_cached_vehicle(id)
            await self._emit_vehicle_event("vehicle.deleted", current, vehicle_id=id)
        return deleted

    async def _get_cached_vehicle(self, vehicle_id: int) -> VehicleModel | None:
        if self._cache is None:
            return None

        started_at = perf_counter()
        try:
            cached = await self._cache.get_text(self._cache_key(vehicle_id))
            if cached is None:
                log_cache_lookup(
                    operation="vehicle_by_id",
                    result="miss",
                    duration_seconds=perf_counter() - started_at,
                )
                return None

            data = json.loads(cached)
            if data["purchased_at_utc"] is not None:
                data["purchased_at_utc"] = datetime.fromisoformat(data["purchased_at_utc"])
            log_cache_lookup(
                operation="vehicle_by_id",
                result="hit",
                duration_seconds=perf_counter() - started_at,
            )
            return VehicleModel(**data)
        except Exception:
            log_cache_lookup(
                operation="vehicle_by_id",
                result="error",
                duration_seconds=perf_counter() - started_at,
            )
            return None

    async def _cache_vehicle(self, vehicle: VehicleModel) -> None:
        if self._cache is None or vehicle.id is None:
            return

        data = vehicle.to_dict()
        if data["purchased_at_utc"] is not None:
            data["purchased_at_utc"] = data["purchased_at_utc"].isoformat()

        try:
            await self._cache.set_text(
                self._cache_key(vehicle.id),
                json.dumps(data),
                ttl_seconds=self._cache_ttl_seconds,
            )
        except Exception:
            return None

    async def _delete_cached_vehicle(self, vehicle_id: int) -> None:
        if self._cache is None:
            return

        try:
            await self._cache.delete_text(self._cache_key(vehicle_id))
        except Exception:
            return None

    @staticmethod
    def _cache_key(vehicle_id: int) -> str:
        return f"vehicle:id:{vehicle_id}"

    async def _emit_vehicle_event(
        self,
        event_type: str,
        vehicle: VehicleModel | None,
        *,
        vehicle_id: int | None = None,
    ) -> None:
        if self._event_producer is None and self._outbox_repo is None:
            return

        resolved_vehicle_id = vehicle.id if vehicle is not None else vehicle_id
        if resolved_vehicle_id is None:
            return

        payload = await self._vehicle_event_payload(vehicle, vehicle_id=resolved_vehicle_id)
        event = EventEnvelope.create(
            event_type=event_type,
            producer="auto-parking-api",
            entity="vehicle",
            entity_id=resolved_vehicle_id,
            payload=payload,
        )
        await self._send_or_queue_event(
            topic=self._event_topic,
            event=event,
            key=str(resolved_vehicle_id),
            log_name="vehicle",
        )
        await self._send_or_queue_event(
            topic=self._audit_event_topic,
            event=event,
            key=str(resolved_vehicle_id),
            log_name="audit",
        )

    async def _send_or_queue_event(
        self,
        *,
        topic: str,
        event: EventEnvelope,
        key: str,
        log_name: str,
    ) -> None:
        if self._outbox_repo is not None:
            await self._outbox_repo.add_event(topic=topic, event=event, key=key)
            return

        if self._event_producer is None:
            return

        try:
            await self._event_producer.publish(topic, event, key=key)
        except Exception:
            logger.warning(
                "Failed to publish %s event: topic=%s event_type=%s entity_id=%s",
                log_name,
                topic,
                event.event_type,
                event.entity_id,
                exc_info=True,
            )

    async def _vehicle_event_payload(
        self,
        vehicle: VehicleModel | None,
        *,
        vehicle_id: int,
    ) -> dict:
        if vehicle is None:
            return {"vehicle_id": vehicle_id, "manager_user_ids": []}
        manager_ids = await self._repo.manager_ids_for_enterprise(vehicle.enterprise_id)
        return {
            "vehicle_id": vehicle_id,
            "vehicle_number": vehicle.vehicle_number,
            "enterprise_id": vehicle.enterprise_id,
            "manager_user_ids": manager_ids,
            "model_id": vehicle.model_id,
            "active_driver_id": vehicle.active_driver_id,
            "driver_ids": list(vehicle.drivers),
            "color": vehicle.color,
        }

    def _build_out(self, vehicle: "Vehicle") -> VehicleModel:
        return VehicleModel(
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
            active_driver_id=vehicle.active_driver_id,
            purchased_at_utc=vehicle.purchased_at_utc,
            enterprise_timezone=(
                vehicle.enterprise.timezone
                if vehicle.__dict__.get("enterprise") is not None
                else None
            ),
        )

    @staticmethod
    def _persistence_data(vehicle: VehicleModel) -> dict:
        return {
            "price": vehicle.price,
            "mileage": vehicle.mileage,
            "vehicle_number": vehicle.vehicle_number.strip().upper(),
            "owners_count": vehicle.owners_count,
            "accident_number": vehicle.accident_number,
            "manufacture_year": vehicle.manufacture_year,
            "model_id": vehicle.model_id,
            "enterprise_id": vehicle.enterprise_id,
            "active_driver_id": vehicle.active_driver_id,
            "color": vehicle.color,
            "purchased_at_utc": vehicle.purchased_at_utc,
        }
