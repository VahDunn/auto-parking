from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from auto_parking.core.domain.user_role import UserRole
from auto_parking.core.security.jwt import decode_access_token


class AdminJWTAuthBackend(AuthenticationBackend):
    def __init__(self, secret_key: str, login_path: str = "/"):
        super().__init__(secret_key=secret_key)
        self.login_path = login_path

    async def login(self, request: Request) -> bool:
        return False

    async def logout(self, request: Request) -> Response | bool:
        response = RedirectResponse(url=self.login_path, status_code=302)
        response.delete_cookie("access_token", path="/")
        return response

    async def authenticate(self, request: Request) -> Response | bool:
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url=self.login_path, status_code=302)

        try:
            payload = decode_access_token(token)
        except Exception:
            response = RedirectResponse(url=self.login_path, status_code=302)
            response.delete_cookie("access_token", path="/")
            return response

        role = payload["role"]
        actor_id = payload["id"]

        if role != UserRole.admin:
            return Response("Forbidden", status_code=403)

        request.state.actor_id = actor_id
        request.state.actor_role = role
        return True
