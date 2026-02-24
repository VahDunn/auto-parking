# tests/test_csrf.py
import pytest
from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient

from auto_parking.core.config import settings
from auto_parking.core.security.basic_auth import verify_user
from auto_parking.core.security.csrf import (
    CSRF_COOKIE,
    CSRF_HEADER,
    csrf_protect,
    new_csrf_token,
    set_csrf_cookie,
)

AUTH = (settings.test_admin_login, settings.test_admin_pass)


def create_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/csrf-token")
    async def get_csrf_token(response: Response, _user=Depends(verify_user)):
        token = new_csrf_token()
        set_csrf_cookie(response, token, secure=False, samesite="lax")
        return {"csrf_token": token}

    @app.post("/protected")
    async def protected_endpoint(
        _user=Depends(verify_user),
        _csrf=Depends(csrf_protect),
    ):
        return {"ok": True}

    return app


@pytest.fixture()
def client() -> TestClient:
    app = create_test_app()
    return TestClient(app)


def test_csrf_token_endpoint_sets_cookie_and_returns_token(client: TestClient):
    r = client.get("/csrf-token", auth=AUTH)
    assert r.status_code == 200

    body_token = r.json().get("csrf_token")
    assert body_token, "csrf_token отсутствует в JSON ответе"

    assert CSRF_COOKIE in r.cookies, "csrf_token cookie не выставилась"
    cookie_token = r.cookies.get(CSRF_COOKIE)
    assert cookie_token, "csrf_token cookie пустая"

    assert cookie_token == body_token


def test_post_without_csrf_returns_403(client: TestClient):
    r = client.post("/protected", auth=AUTH)
    assert r.status_code == 403
    assert r.json().get("detail") in {"CSRF token missing", "CSRF validation failed"}


def test_post_with_invalid_csrf_returns_403(client: TestClient):
    r = client.post(
        "/protected",
        auth=AUTH,
        cookies={CSRF_COOKIE: "cookie_token"},
        headers={CSRF_HEADER: "header_token"},
    )
    assert r.status_code == 403
    assert r.json().get("detail") in {"CSRF token invalid", "CSRF validation failed"}


def test_post_with_valid_csrf_succeeds(client: TestClient):
    r = client.get("/csrf-token", auth=AUTH)
    assert r.status_code == 200
    token = r.json()["csrf_token"]
    r2 = client.post(
        "/protected",
        auth=AUTH,
        cookies={CSRF_COOKIE: token},
        headers={CSRF_HEADER: token},
    )
    assert r2.status_code == 200
    assert r2.json() == {"ok": True}
