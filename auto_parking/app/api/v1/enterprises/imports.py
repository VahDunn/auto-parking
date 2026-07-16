from typing import TYPE_CHECKING

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from auto_parking.app.api.v1.enterprises.common import dep_actor_guard
from auto_parking.app.deps.services import dep_import_service
from auto_parking.core.domain.enums.import_export_format import ImportFormat

if TYPE_CHECKING:
    from auto_parking.app.service.import_ import ImportService

router = APIRouter()


@router.post(
    "/import",
    dependencies=[dep_actor_guard],
)
async def import_enterprise(
    format: ImportFormat = Query(...),
    file: UploadFile = File(...),
    service: "ImportService" = dep_import_service,
):
    raw = await file.read()

    try:
        if format == ImportFormat.json:
            return await service.import_enterprise_json(raw)
        if format == ImportFormat.csv:
            return await service.import_enterprise_csv(raw)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
