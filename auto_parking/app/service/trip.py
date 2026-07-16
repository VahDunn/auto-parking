from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2.shape import to_shape
from shapely.geometry import Point

from auto_parking.app.filter import TripFilter
from auto_parking.core.domain.models import (
    TripModel,
    TripPointModel,
)
from auto_parking.core.utils.datetime import to_enterprise_tz, to_utc

if TYPE_CHECKING:
    from auto_parking.app.ports.geocoding import ReverseGeocoder
    from auto_parking.app.service.notification import NotificationService
    from auto_parking.infrastructure.db.models import Trip, VehicleGpsPoint
    from auto_parking.infrastructure.db.repositories.trip import TripRepository


class TripService:
    def __init__(
        self,
        repo: "TripRepository",
        geocoder: "ReverseGeocoder | None" = None,
        notification_service: "NotificationService | None" = None,
    ) -> None:
        self._repo = repo
        self._geocoder = geocoder
        self._notification_service = notification_service

    async def get(self, filter_obj: TripFilter) -> list[TripModel]:
        trips: Sequence[Trip] = await self._repo.get(filter_obj)
        return [await self._build_out(t) for t in trips]

    async def get_vehicle_trips_in_range(
        self,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
        include_addresses: bool = True,
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
        return [await self._build_out(t, include_addresses=include_addresses) for t in trips]

    async def get_by_id(self, trip_id: int) -> TripModel | None:
        trip: Trip | None = await self._repo.get_by_id(trip_id)
        return await self._build_out(trip) if trip else None

    async def create(
        self,
        trip_model: TripModel,
        *,
        include_addresses: bool = True,
    ) -> TripModel:
        trip: Trip = await self._repo.create(self._persistence_data(trip_model))
        if self._notification_service is not None:
            await self._notification_service.notify_trip_created(trip)
        return await self._build_out(trip, include_addresses=include_addresses)

    async def update(self, trip_id: int, trip_model: TripModel) -> TripModel | None:
        if trip_model.ended_at_utc < trip_model.started_at_utc:
            raise ValueError("ended_at must be greater than or equal to started_at")

        trip = await self._repo.update(trip_id, self._persistence_data(trip_model))
        return await self._build_out(trip) if trip else None

    async def delete(self, trip_id: int) -> bool:
        return await self._repo.delete(trip_id)

    async def _build_out(self, trip: "Trip", *, include_addresses: bool = True) -> TripModel:
        enterprise = trip.vehicle.enterprise if trip.vehicle else None
        tz = enterprise.timezone if enterprise else None

        return TripModel(
            id=trip.id,
            vehicle_id=trip.vehicle_id,
            started_at_utc=trip.started_at_utc,
            ended_at_utc=trip.ended_at_utc,
            start_point_id=getattr(trip, "start_point_id", trip.start_point.id),
            end_point_id=getattr(trip, "end_point_id", trip.end_point.id),
            started_at_enterprise=to_enterprise_tz(trip.started_at_utc, tz),
            ended_at_enterprise=to_enterprise_tz(trip.ended_at_utc, tz),
            enterprise_timezone=tz or "UTC",
            start_point=await self._build_point_out(
                trip.start_point,
                tz,
                include_address=include_addresses,
            ),
            end_point=await self._build_point_out(
                trip.end_point,
                tz,
                include_address=include_addresses,
            ),
        )

    @staticmethod
    def _persistence_data(trip: TripModel) -> dict:
        return {
            "vehicle_id": trip.vehicle_id,
            "started_at_utc": trip.started_at_utc,
            "ended_at_utc": trip.ended_at_utc,
            "start_point_id": trip.start_point_id,
            "end_point_id": trip.end_point_id,
        }

    async def _build_point_out(
        self,
        point: "VehicleGpsPoint",
        enterprise_tz: str | None,
        *,
        include_address: bool = True,
    ) -> TripPointModel:
        shapely_point = to_shape(point.position)
        if not isinstance(shapely_point, Point):
            raise ValueError("Expected Point geometry")

        latitude = shapely_point.y
        longitude = shapely_point.x

        address: str | None = None
        if include_address and self._geocoder is not None:
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
