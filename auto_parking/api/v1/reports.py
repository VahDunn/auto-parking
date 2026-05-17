import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Response, status

from auto_parking.api.schemas.report import ReportCreate, ReportInfo, ReportOut
from auto_parking.core.domain import ExportFormat
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import dep_report_service, dep_reports_pdf_service
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.service.report import ReportService
from auto_parking.service.report_pdf import ReportPdfBuilder

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


@router.get(
    "/{id}/export",
    dependencies=[dep_actor_guard],
)
async def export_report(
    id: int,
    format: ExportFormat = ExportFormat.json,
    visible_enterprise_ids: set[int] | None = dep_visible_ids,
    service: ReportService = dep_report_service,
    pdf_service: ReportPdfBuilder = dep_reports_pdf_service,
):
    report = await service.get_by_id(id)

    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if visible_enterprise_ids is not None and report.enterprise_id not in visible_enterprise_ids:
        raise HTTPException(status_code=403, detail="Forbidden")

    filename = f"report_{report.id}"

    if format == ExportFormat.pdf:
        pdf_bytes = pdf_service.build(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": (f'attachment; filename="{filename}.pdf"')},
        )

    if format == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "report_id",
                "name",
                "report_type",
                "period",
                "date_from",
                "date_to",
                "enterprise_id",
                "vehicle_id",
                "time",
                "value",
                "extra_json",
            ]
        )

        for item in report.result_json:
            writer.writerow(
                [
                    report.id,
                    report.name,
                    report.report_type,
                    report.period,
                    report.date_from.isoformat(),
                    report.date_to.isoformat(),
                    report.enterprise_id,
                    report.vehicle_id or "",
                    item.get("time", ""),
                    item.get("value", ""),
                    json.dumps(item.get("extra", {}), ensure_ascii=False),
                ]
            )

        return Response(
            content=output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )

    payload = {
        "id": report.id,
        "name": report.name,
        "report_type": report.report_type,
        "period": report.period,
        "date_from": report.date_from.isoformat(),
        "date_to": report.date_to.isoformat(),
        "enterprise_id": report.enterprise_id,
        "vehicle_id": report.vehicle_id,
        "params_json": report.params_json,
        "result_json": report.result_json,
        "created_at": report.created_at.isoformat(),
    }

    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
    )


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

    return await service.delete(id)
