from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def get_token(
    request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> str:
    if creds and creds.scheme.lower() == "bearer" and creds.credentials:
        return creds.credentials.strip()

    cookie = request.cookies.get("access_token")
    if cookie:
        return cookie.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
