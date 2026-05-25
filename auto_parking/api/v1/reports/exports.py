import csv
import io
import json

from fastapi import APIRouter, HTTPException, Response

from auto_parking.api.v1.reports.common import (
    dep_actor_guard,
    dep_visible_ids,
    ensure_report_visible,
)
from auto_parking.core.enums import ExportFormat
from auto_parking.deps.services import dep_report_service, dep_reports_pdf_service
from auto_parking.service.report import ReportService
from auto_parking.service.report_pdf import ReportPdfBuilder

router = APIRouter()


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

    ensure_report_visible(report, visible_enterprise_ids)

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
