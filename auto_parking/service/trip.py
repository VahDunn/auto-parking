from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2.shape import to_shape
from shapely.geometry import Point

from auto_parking.core.domain.models import TripCreateModel, TripModel, TripPointModel, TripUpdateModel
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc
from auto_parking.filter import TripFilter

if TYPE_CHECKING:
    from auto_parking.db.models import Trip, VehicleGpsPoint
    from auto_parking.integrations.geocoding.base import ReverseGeocoder
    from auto_parking.repo.trip import TripRepository


class TripService:
    def __init__(
        self,
        repo: "TripRepository",
        geocoder: "ReverseGeocoder | None" = None,
    ) -> None:
        self._repo = repo
        self._geocoder = geocoder

    async def get(self, filter_obj: TripFilter) -> list[TripModel]:
        trips: Sequence[Trip] = await self._repo.get(filter_obj)
        return [await self._build_out(t) for t in trips]

    async def get_vehicle_trips_in_range(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[TripModel]:
        date_from_utc = to_utc(date_from)
        date_to_utc = to_utc(date_to)

        trips = await self._repo.get(
            TripFilter(
                vehicle_id=vehicle_id,
                started_from=date_from_utc,
                ended_to=date_to_utc,
                limit=None,
                offset=None,
            )
        )
        return [await self._build_out(t) for t in trips]

    async def get_by_id(self, trip_id: int) -> TripModel | None:
        trip: Trip | None = await self._repo.get_by_id(trip_id)
        return await self._build_out(trip) if trip else None

    async def create(self, payload: TripCreateModel) -> TripModel:
        data = payload.to_dict()
        started_at = data.pop("started_at")
        ended_at = data.pop("ended_at")

        data["started_at_utc"] = to_utc(started_at)
        data["ended_at_utc"] = to_utc(ended_at)

        trip: Trip = await self._repo.create(data)
        return await self._build_out(trip)

    async def update(self, trip_id: int, payload: TripUpdateModel) -> TripModel | None:
        trip = await self._repo.get_by_id(trip_id)
        if not trip:
            return None

        payload_dump = dict(payload.changes)

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
        return await self._build_out(trip) if trip else None

    async def delete(self, trip_id: int) -> bool:
        return await self._repo.delete(trip_id)

    async def _build_out(self, trip: "Trip") -> TripModel:
        enterprise = trip.vehicle.enterprise if trip.vehicle else None
        tz = enterprise.timezone if enterprise else None

        return TripModel(
            id=trip.id,
            vehicle_id=trip.vehicle_id,
            started_at_utc=trip.started_at_utc,
            ended_at_utc=trip.ended_at_utc,
            started_at_enterprise=to_enterprise_tz(trip.started_at_utc, tz),
            ended_at_enterprise=to_enterprise_tz(trip.ended_at_utc, tz),
            enterprise_timezone=tz or "UTC",
            start_point=await self._build_point_out(trip.start_point, tz),
            end_point=await self._build_point_out(trip.end_point, tz),
        )

    async def _build_point_out(
        self,
        point: "VehicleGpsPoint",
        enterprise_tz: str | None,
    ) -> TripPointModel:
        shapely_point = to_shape(point.position)
        if not isinstance(shapely_point, Point):
            raise ValueError("Expected Point geometry")

        latitude = shapely_point.y
        longitude = shapely_point.x

        address: str | None = None
        if self._geocoder is not None:
            address = await self._geocoder.reverse_geocode(
                latitude=latitude,
                longitude=longitude,
            )

        return TripPointModel(
            id=point.id,
            recorded_at_utc=point.recorded_at_utc,
            recorded_at_enterprise=to_enterprise_tz(
                point.recorded_at_utc,
                enterprise_tz,
            ),
            latitude=latitude,
            longitude=longitude,
            address=address,
        )
