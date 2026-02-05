from fastapi import Depends

from auto_parking.api.schemas.driver import DriverFilter
from auto_parking.api.schemas.vehicle import VehicleFilter
from auto_parking.deps.commons import dep_parse_ids


def driver_filter(
    ids: list[int] | None = dep_parse_ids,
    enterprise_id: int | None = None,
) -> DriverFilter:
    return DriverFilter(
        ids=ids,
        enterprise_id=enterprise_id,
    )


dep_driver_filter = Depends(driver_filter)


def vehicle_filter(
    ids: list[int] | None = dep_parse_ids,
    enterprise_id: int | None = None,
) -> VehicleFilter:
    return VehicleFilter(
        ids=ids,
        enterprise_id=enterprise_id,
    )


dep_vehicle_filter = Depends(vehicle_filter)
