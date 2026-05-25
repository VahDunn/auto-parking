from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query

from auto_parking.api.v1.enterprises.common import (
    dep_actor_guard,
    dep_visible_ids,
    ensure_aware_datetime,
    ensure_enterprise_visible,
    ensure_valid_date_range,
    export_response,
)
from auto_parking.core.domain.enums.import_export_format import ExportFormat
from auto_parking.core.errors import NotFoundError
from auto_parking.deps.services import dep_export_service

if TYPE_CHECKING:
    from auto_parking.service.export import ExportService

router = APIRouter()


@router.get(
    "/{id}/export",
    dependencies=[dep_actor_guard],
)
async def export_enterprise_full(
    id: int,
    date_from: datetime = Query(..., description="Timezone-aware datetime"),
    date_to: datetime = Query(..., description="Timezone-aware datetime"),
    format: ExportFormat = Query(ExportFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "ExportService" = dep_export_service,
):
    ensure_aware_datetime(date_from, "date_from")
    ensure_aware_datetime(date_to, "date_to")
    ensure_valid_date_range(date_from, date_to)
    ensure_enterprise_visible(id, visible_enterprise_ids)

    try:
        content = await service.export_enterprise_full(
            enterprise_id=id,
            date_from=date_from,
            date_to=date_to,
            format=format,
        )
    except NotFoundError as err:
        raise HTTPException(status_code=404, detail=err.message) from err

    return export_response(
        content=content,
        format=format,
        filename_base=f"enterprise_{id}_full_export",
    )


@router.get(
    "/{id}/export-vehicles",
    dependencies=[dep_actor_guard],
)
async def export_enterprise_vehicles(
    id: int,
    format: ExportFormat = Query(ExportFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "ExportService" = dep_export_service,
):
    ensure_enterprise_visible(id, visible_enterprise_ids)

    try:
        content = await service.export_enterprise_vehicles(
            enterprise_id=id,
            format=format,
        )
    except NotFoundError as err:
        raise HTTPException(status_code=404, detail=err.message) from err

    return export_response(
        content=content,
        format=format,
        filename_base=f"enterprise_{id}_vehicles_export",
    )


@router.get(
    "/{id}/export-guid-dump",
    dependencies=[dep_actor_guard],
)
async def export_enterprise_guid_dump(
    id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    format: ExportFormat = Query(ExportFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "ExportService" = dep_export_service,
):
    ensure_aware_datetime(date_from, "date_from")
    ensure_aware_datetime(date_to, "date_to")
    ensure_valid_date_range(date_from, date_to)
    ensure_enterprise_visible(id, visible_enterprise_ids)

    try:
        content = await service.export_enterprise_guid_dump(
            enterprise_id=id,
            date_from=date_from,
            date_to=date_to,
            format=format,
        )
    except NotFoundError as err:
        raise HTTPException(status_code=404, detail=err.message) from err

    return export_response(
        content=content,
        format=format,
        filename_base=f"enterprise_{id}_guid_dump",
    )
