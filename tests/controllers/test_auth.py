from types import SimpleNamespace

import pytest

from auto_parking.core.domain.enums import UserRole
from tests.conftest import set_user_service_override

pytestmark = pytest.mark.asyncio


async def test_auth_login_success_sets_cookie(client, overrides, user_service_mock, monkeypatch):
    monkeypatch.setattr("auto_parking.api.v1.auth.verify_password", lambda *_: True)
    set_user_service_override(overrides, user_service_mock)
    user_service_mock.get.return_value = [
        SimpleNamespace(
            id=42,
            username="manager",
            password_hash="hashed-secret",
            role=UserRole.manager,
        )
    ]

    response = await client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert "access_token=" in response.headers["set-cookie"]


async def test_auth_login_returns_401_for_bad_password(
    client,
    overrides,
    user_service_mock,
    monkeypatch,
):
    monkeypatch.setattr("auto_parking.api.v1.auth.verify_password", lambda *_: False)
    set_user_service_override(overrides, user_service_mock)
    user_service_mock.get.return_value = [
        SimpleNamespace(
            id=42,
            username="manager",
            password_hash="hashed-secret",
            role=UserRole.manager,
        )
    ]

    response = await client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong login or password"
