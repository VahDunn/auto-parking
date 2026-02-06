import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from auto_parking.core.config import settings

security = HTTPBasic()  # ← ВАЖНО

USERNAME = settings.test_admin_login
PASSWORD = settings.test_admin_pass


def verify_user(credentials: HTTPBasicCredentials = Depends(security)):  # noqa
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong login or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
