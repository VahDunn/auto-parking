from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status

from auto_parking.core.enums.user_role import UserRole
from auto_parking.core.errors import ConflictError
from auto_parking.core.models import VehicleModel
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.services import dep_enterprise_service, dep_vehicle_service
from auto_parking.deps.visibility import get_visible_enterprise_ids
from auto_parking.main import app as fastapi_app

pytestmark = pytest.mark.asyncio


def show_response(r):
    print("\n--- RESPONSE ---")
    print("STATUS:", r.status_code)
    print("BODY:", r.json())
    print("---------------\n")


class FakeActor:
    def __init__(self, role: UserRole, id: int = 1):
        self.role = role
        self.id = id


def dep_callable(dep_obj):
    return getattr(dep_obj, "dependency", dep_obj)


async def _guard_403():
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def make_vehicle_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.create = AsyncMock()
    svc.update = AsyncMock()
    svc.delete = AsyncMock()
    return svc


def make_enterprise_service_mock():
    svc = AsyncMock()
    svc.get = AsyncMock()
    svc.get_by_id = AsyncMock()
    svc.delete = AsyncMock()
    return svc


async def test_all_required_status_codes(client, overrides):
    fastapi_app.dependency_overrides.clear()

    req = await client.get("/api/vehicles")
    assert req.status_code == 401

    actor_manager = FakeActor(UserRole.manager, id=1)

    async def _guard_manager():
        return actor_manager

    async def _visible_ids():
        return {4}

    vehicle_svc = make_vehicle_service_mock()
    enterprise_svc = make_enterprise_service_mock()

    async def _dep_vehicle_service():
        return vehicle_svc

    async def _dep_enterprise_service():
        return enterprise_svc

    overrides[require_manager_or_higher] = _guard_manager
    overrides[get_visible_enterprise_ids] = _visible_ids
    overrides[dep_callable(dep_vehicle_service)] = _dep_vehicle_service
    overrides[dep_callable(dep_enterprise_service)] = _dep_enterprise_service

    overrides[require_manager_or_higher] = _guard_403
    req = await client.get("/api/vehicles")
    assert req.status_code == 403

    overrides[require_manager_or_higher] = _guard_manager

    vehicle_svc.get_by_id.return_value = None
    req = await client.get("/api/vehicles/999")
    assert req.status_code == 404

    created_dict = {
        "id": 5,
        "price": 100,
        "mileage": 10,
        "vehicle_number": "А123ВС77",
        "owners_count": 1,
        "accident_number": 0,
        "manufacture_year": 2020,
        "model_id": 1,
        "color": "black",
        "enterprise_id": 4,
        "drivers": [],
        "active_driver_id": -1,
        "purchased_at_utc": None,
        "purchased_at_enterprise": None,
        "enterprise_timezone": "UTC",
    }
    updated_dict = {**created_dict, "price": 999}

    created = VehicleModel(**created_dict)
    updated = VehicleModel(**updated_dict)

    vehicle_svc.create.return_value = created
    vehicle_svc.get_by_id.return_value = created
    vehicle_svc.update.return_value = updated
    vehicle_svc.delete.return_value = True

    post_payload = {
        "price": 100,
        "mileage": 10,
        "vehicle_number": "А123ВС77",
        "owners_count": 1,
        "accident_number": 0,
        "manufacture_year": 2020,
        "model_id": 1,
        "enterprise_id": 4,
        "color": "black",
        "purchased_at": "2026-04-10T08:00:00+03:00",
    }

    req = await client.post("/api/vehicles", json=post_payload)
    assert req.status_code == 201

    req = await client.patch("/api/vehicles/5", json={"price": 999})
    assert req.status_code == 200

    req = await client.delete("/api/vehicles/5")
    assert req.status_code == 204

    enterprise_svc.delete.side_effect = ConflictError("Enterprise is visible to other managers")
    req = await client.delete("/api/enterprises/4")
    assert req.status_code == 409

    req = await client.post(
        "/api/vehicles",
        json={
            "price": 100,
            "mileage": 10,
            "vehicle_number": "А123ВС77",
            "owners_count": 1,
            "accident_number": 0,
            "manufacture_year": 2020,
            "model_id": 1,
            "color": "black",
            "purchased_at": "2026-04-10T08:00:00+03:00",
        },
    )
    show_response(req)
    assert req.status_code == 400

    req = await client.post(
        "/api/vehicles",
        json={
            "price": "abc",
            "mileage": 10,
            "vehicle_number": "А123ВС77",
            "owners_count": 1,
            "accident_number": 0,
            "manufacture_year": 2020,
            "model_id": 1,
            "enterprise_id": 4,
            "color": "black",
            "purchased_at": "2026-04-10T08:00:00+03:00",
        },
    )
    show_response(req)
    assert req.status_code == 400
