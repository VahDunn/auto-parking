import hmac
import secrets
from typing import Literal

from fastapi import Header, HTTPException, Request, Response, status

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(
    response: Response,
    token: str,
    *,
    secure: bool = False,
    samesite: Literal["lax", "strict", "none"] = "lax",
) -> None:
    response.set_cookie(
        "csrf_token",
        token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )


def csrf_protect(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE)

    if not cookie_token or not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    if not hmac.compare_digest(cookie_token, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid",
        )
