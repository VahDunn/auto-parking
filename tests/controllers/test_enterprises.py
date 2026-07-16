import pytest

from auto_parking.app.filter import EnterpriseFilter
from auto_parking.core.domain.enums import UserRole
from auto_parking.core.errors import NotFoundError
from tests.conftest import (
    set_actor_override,
    set_enterprise_service_override,
    set_export_service_override,
    set_import_service_override,
    set_visible_ids_override,
)
from tests.factories import enterprise_model

pytestmark = pytest.mark.asyncio


async def test_enterprises_crud_and_visibility(client, overrides, enterprise_service_mock):
    set_actor_override(overrides, UserRole.manager, actor_id=5)
    set_visible_ids_override(overrides, {10})
    set_enterprise_service_override(overrides, enterprise_service_mock)
    enterprise_service_mock.get.return_value = [enterprise_model()]
    enterprise_service_mock.get_by_id.return_value = enterprise_model()

    list_response = await client.get("/api/enterprises")
    detail_response = await client.get("/api/enterprises/10")
    delete_response = await client.delete("/api/enterprises/10")
    forbidden_response = await client.get("/api/enterprises/20")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == 10
    assert detail_response.status_code == 200
    assert delete_response.status_code == 204
    assert forbidden_response.status_code == 403

    filter_obj = enterprise_service_mock.get.await_args.args[0]
    assert isinstance(filter_obj, EnterpriseFilter)
    assert filter_obj.ids == [10]


async def test_enterprise_exports_and_import_success(
    client,
    overrides,
    export_service_mock,
    import_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_export_service_override(overrides, export_service_mock)
    set_import_service_override(overrides, import_service_mock)
    export_service_mock.export_enterprise_full.return_value = '{"enterprise": {}}'
    export_service_mock.export_enterprise_vehicles.return_value = "vehicle_id\n"
    export_service_mock.export_enterprise_guid_dump.return_value = '{"dump": true}'
    import_service_mock.import_enterprise_json.return_value = {"status": "ok"}

    full_response = await client.get(
        "/api/enterprises/10/export",
        params={
            "date_from": "2026-01-01T00:00:00+00:00",
            "date_to": "2026-01-02T00:00:00+00:00",
            "format": "json",
        },
    )
    vehicles_response = await client.get(
        "/api/enterprises/10/export-vehicles",
        params={"format": "csv"},
    )
    guid_response = await client.get(
        "/api/enterprises/10/export-guid-dump",
        params={
            "date_from": "2026-01-01T00:00:00+00:00",
            "date_to": "2026-01-02T00:00:00+00:00",
            "format": "json",
        },
    )
    import_response = await client.post(
        "/api/enterprises/import",
        params={"format": "json"},
        files={"file": ("enterprise.json", b"{}", "application/json")},
    )

    assert full_response.status_code == 200
    assert vehicles_response.status_code == 200
    assert vehicles_response.headers["content-type"] == "text/csv; charset=utf-8"
    assert guid_response.status_code == 200
    assert import_response.status_code == 200
    assert import_response.json() == {"status": "ok"}


async def test_enterprise_export_returns_404_from_service(
    client,
    overrides,
    export_service_mock,
):
    set_actor_override(overrides, UserRole.manager)
    set_visible_ids_override(overrides, {10})
    set_export_service_override(overrides, export_service_mock)
    export_service_mock.export_enterprise_full.side_effect = NotFoundError("Enterprise not found")

    response = await client.get(
        "/api/enterprises/10/export",
        params={
            "date_from": "2026-01-01T00:00:00+00:00",
            "date_to": "2026-01-02T00:00:00+00:00",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Enterprise not found"
