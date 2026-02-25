import base64
import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from auto_parking.core.config import settings


class AdminBasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, path_prefix: str = "/admin"):
        super().__init__(app)
        self._path_prefix = path_prefix

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(self._path_prefix):
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return self._challenge()

        try:
            encoded = auth.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode()
            username, password = decoded.split(":", 1)
        except Exception:
            return self._challenge()

        valid_user = secrets.compare_digest(username, settings.test_admin_login)
        valid_pass = secrets.compare_digest(password, settings.test_admin_pass)

        if not (valid_user and valid_pass):
            return self._challenge()

        return await call_next(request)

    def _challenge(self):
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Admin"'},
        )
