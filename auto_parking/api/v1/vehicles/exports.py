from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query

from auto_parking.api.v1.vehicles.common import (
    dep_actor_guard,
    dep_visible_ids,
    ensure_aware_datetime,
    ensure_enterprise_visible,
    ensure_valid_date_range,
    export_response,
)
from auto_parking.core.domain.enums.import_export_format import ExportFormat
from auto_parking.deps.services import dep_export_service, dep_vehicle_service
from auto_parking.service.vehicle import VehicleService

if TYPE_CHECKING:
    from auto_parking.service.export import ExportService

router = APIRouter()


@router.get(
    "/{id}/export-trips",
    dependencies=[dep_actor_guard],
)
async def export_vehicle_trips(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    format: ExportFormat = Query(ExportFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    vehicle_service: VehicleService = dep_vehicle_service,
    service: "ExportService" = dep_export_service,
):
    ensure_aware_datetime(date_from, "date_from")
    ensure_aware_datetime(date_to, "date_to")
    ensure_valid_date_range(date_from, date_to)

    vehicle = await vehicle_service.get_by_id(id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    ensure_enterprise_visible(vehicle.enterprise_id, visible_enterprise_ids)

    content = await service.export_vehicle_trips(
        vehicle_id=id,
        date_from=date_from,
        date_to=date_to,
        format=format,
    )

    return export_response(
        content=content,
        format=format,
        filename_base=f"vehicle_{id}_trips_export",
    )
