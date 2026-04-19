from collections.abc import Sequence
from typing import TYPE_CHECKING

from auto_parking.api.schemas.trip import TripFilter, TripOut
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc

if TYPE_CHECKING:
    from auto_parking.api.schemas.trip import TripCreate, TripUpdate
    from auto_parking.db.models import Trip
    from auto_parking.repo.trip import TripRepository


class TripService:
    def __init__(self, repo: "TripRepository") -> None:
        self._repo = repo

    async def get(self, filter_obj: TripFilter) -> list[TripOut]:
        trips: Sequence[Trip] = await self._repo.get(filter_obj)
        return [self._build_out(t) for t in trips]

    async def get_by_id(self, trip_id: int) -> TripOut | None:
        trip: Trip | None = await self._repo.get_by_id(trip_id)
        return self._build_out(trip) if trip else None

    async def create(self, payload: "TripCreate") -> TripOut:
        data = payload.model_dump()
        started_at = data.pop("started_at")
        ended_at = data.pop("ended_at")

        data["started_at_utc"] = to_utc(started_at)
        data["ended_at_utc"] = to_utc(ended_at)

        trip: Trip = await self._repo.create(data)
        return self._build_out(trip)

    async def update(self, trip_id: int, payload: "TripUpdate") -> TripOut | None:
        trip = await self._repo.get_by_id(trip_id)
        if not trip:
            return None

        payload_dump = payload.model_dump(exclude_unset=True)

        started_at_utc = trip.started_at_utc
        ended_at_utc = trip.ended_at_utc

        if "started_at" in payload_dump:
            started_at_utc = to_utc(payload_dump.pop("started_at"))
            payload_dump["started_at_utc"] = started_at_utc

        if "ended_at" in payload_dump:
            ended_at_utc = to_utc(payload_dump.pop("ended_at"))
            payload_dump["ended_at_utc"] = ended_at_utc

        if ended_at_utc < started_at_utc:
            raise ValueError("ended_at must be greater than or equal to started_at")

        trip = await self._repo.update(trip_id, payload_dump)
        return self._build_out(trip) if trip else None

    async def delete(self, trip_id: int) -> bool:
        return await self._repo.delete(trip_id)

    def _build_out(self, trip: "Trip") -> TripOut:
        enterprise = trip.vehicle.enterprise if trip.vehicle else None
        tz = enterprise.timezone if enterprise else None

        return TripOut(
            id=trip.id,
            vehicle_id=trip.vehicle_id,
            started_at_utc=trip.started_at_utc,
            ended_at_utc=trip.ended_at_utc,
            started_at_enterprise=to_enterprise_tz(trip.started_at_utc, tz),
            ended_at_enterprise=to_enterprise_tz(trip.ended_at_utc, tz),
            enterprise_timezone=tz or "UTC",
        )
