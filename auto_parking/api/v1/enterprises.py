import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from auto_parking.api.schemas.enterprise import EnterpriseFilter, EnterpriseOut
from auto_parking.core.domain.export_format import ExportFormat
from auto_parking.core.errors import NotFoundError
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import dep_enterprise_service, dep_export_service
from auto_parking.deps.visibility import get_visible_enterprise_ids

if TYPE_CHECKING:
    from auto_parking.service.enterprise import EnterpriseService
    from auto_parking.service.export import ExportService

router = APIRouter()
logger = logging.getLogger(__name__)

dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


@router.get("", response_model=list[EnterpriseOut])
async def get_enterprises(
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    ids = None if visible_enterprise_ids is None else list(visible_enterprise_ids)
    return await service.get(EnterpriseFilter(ids=ids))


@router.get("/{id}", response_model=EnterpriseOut)
async def get_enterprise(
    id: int,
    _actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    enterprise = await service.get_by_id(id)
    if visible_enterprise_ids is not None and id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return enterprise


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enterprise(
    id: int,
    actor=dep_actor_guard,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "EnterpriseService" = dep_enterprise_service,
):
    if visible_enterprise_ids is not None and id not in visible_enterprise_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    await service.delete(id, actor)
    return


@router.get(
    "/{id}/export",
    dependencies=[dep_actor_guard],
)
async def export_enterprise(
    id: int,
    date_from: datetime = Query(..., description="Timezone-aware datetime"),
    date_to: datetime = Query(..., description="Timezone-aware datetime"),
    format: ExportFormat = Query(ExportFormat.json),
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: "ExportService" = dep_export_service,
):
    if date_from.tzinfo is None or date_from.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be timezone-aware",
        )

    if date_to.tzinfo is None or date_to.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be timezone-aware",
        )

    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )

    if visible_enterprise_ids is not None and id not in visible_enterprise_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    try:
        content = await service.export_enterprise_full(
            enterprise_id=id,
            date_from=date_from,
            date_to=date_to,
            format=format,
        )
    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err.message,
        ) from err

    if format == ExportFormat.csv:
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="enterprise_{id}_export.csv"'},
        )

    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="enterprise_{id}_export.json"'},
    )
