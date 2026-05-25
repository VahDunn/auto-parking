import pytest

from auto_parking.core.domain.enums import ReportType, UserRole
from auto_parking.core.domain.models import ReportInfoModel
from tests.conftest import (
    set_actor_override,
    set_report_service_override,
    set_reports_pdf_service_override,
    set_visible_ids_override,
)
from tests.factories import report_model

pytestmark = pytest.mark.asyncio


async def test_reports_crud_and_exports(
    client,
    overrides,
    report_service_mock,
    reports_pdf_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_report_service_override(overrides, report_service_mock)
    set_reports_pdf_service_override(overrides, reports_pdf_service_mock)
    report = report_model()
    report_service_mock.get_available_reports.return_value = [
        ReportInfoModel(
            type=ReportType.vehicle_mileage,
            title="Mileage",
            description="Mileage report",
            parameters=["vehicle_id"],
        )
    ]
    report_service_mock.get_all.return_value = [report]
    report_service_mock.get_by_id.return_value = report
    report_service_mock.create.return_value = report
    report_service_mock.rebuild.return_value = report
    report_service_mock.delete.return_value = True

    create_payload = {
        "name": "Mileage",
        "report_type": "vehicle_mileage",
        "period": "day",
        "date_from": "2026-01-01T00:00:00+00:00",
        "date_to": "2026-01-02T00:00:00+00:00",
        "enterprise_id": 10,
        "vehicle_id": 1,
        "params_json": {},
    }

    assert (await client.get("/api/reports/types")).status_code == 200
    assert (await client.get("/api/reports")).status_code == 200
    assert (await client.get("/api/reports/3")).status_code == 200
    assert (await client.post("/api/reports", json=create_payload)).status_code == 201
    assert (await client.post("/api/reports/3/rebuild")).status_code == 200
    assert (await client.delete("/api/reports/3")).status_code == 204

    json_export = await client.get("/api/reports/3/export", params={"format": "json"})
    csv_export = await client.get("/api/reports/3/export", params={"format": "csv"})
    pdf_export = await client.get("/api/reports/3/export", params={"format": "pdf"})

    assert json_export.status_code == 200
    assert json_export.headers["content-type"] == "application/json; charset=utf-8"
    assert csv_export.status_code == 200
    assert csv_export.headers["content-type"] == "text/csv; charset=utf-8"
    assert pdf_export.status_code == 200
    assert pdf_export.headers["content-type"] == "application/pdf"


async def test_reports_validate_visibility_and_date_range(
    client,
    overrides,
    report_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_report_service_override(overrides, report_service_mock)
    report_service_mock.get_by_id.return_value = report_model(enterprise_id=20)

    hidden_response = await client.get("/api/reports/3")
    bad_range_response = await client.post(
        "/api/reports",
        json={
            "name": "Mileage",
            "report_type": "vehicle_mileage",
            "period": "day",
            "date_from": "2026-01-02T00:00:00+00:00",
            "date_to": "2026-01-01T00:00:00+00:00",
            "enterprise_id": 10,
            "vehicle_id": 1,
            "params_json": {},
        },
    )

    assert hidden_response.status_code == 403
    assert bad_range_response.status_code == 400
