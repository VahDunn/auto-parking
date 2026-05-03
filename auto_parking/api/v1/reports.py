from fastapi import APIRouter, Depends, HTTPException, status

from auto_parking.api.schemas.report import ReportCreate, ReportInfo, ReportOut
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import dep_report_service
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.service.report import ReportService

router = APIRouter()

dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


@router.get(
    "/types",
    response_model=list[ReportInfo],
    dependencies=[dep_actor_guard],
)
async def get_report_types(
    service: ReportService = dep_report_service,
):
    return await service.get_available_reports()


@router.get(
    "",
    response_model=list[ReportOut],
    dependencies=[dep_actor_guard],
)
async def get_reports(
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: ReportService = dep_report_service,
):
    return await service.get_all(visible_enterprise_ids)


@router.get(
    "/{id}",
    response_model=ReportOut,
    dependencies=[dep_actor_guard],
)
async def get_report(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: ReportService = dep_report_service,
):
    report = await service.get_by_id(id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if visible_enterprise_ids is not None and report.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=403, detail="Forbidden")

    return report


@router.post(
    "",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[dep_actor_guard],
)
async def create_report(
    payload: ReportCreate,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: ReportService = dep_report_service,
):
    if visible_enterprise_ids is not None and payload.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.date_to < payload.date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")

    try:
        return await service.create(payload)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@router.post(
    "/{id}/rebuild",
    response_model=ReportOut,
    dependencies=[dep_actor_guard],
)
async def rebuild_report(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: ReportService = dep_report_service,
):
    old_report = await service.get_by_id(id)
    if old_report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if (
        visible_enterprise_ids is not None
        and old_report.enterprise_id not in visible_enterprise_ids
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        report = await service.rebuild(id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[dep_actor_guard],
)
async def delete_report(
    id: int,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: ReportService = dep_report_service,
):
    report = await service.get_by_id(id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if visible_enterprise_ids is not None and report.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=403, detail="Forbidden")

    await service.delete(id)
