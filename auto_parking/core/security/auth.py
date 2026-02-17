import logging
import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from auto_parking.api.schemas.manager import ManagerFilter
from auto_parking.core.security.basic_auth import PASSWORD, USERNAME, sec_dep
from auto_parking.core.security.passwords import verify_password
from auto_parking.deps.services import dep_manager_service

if TYPE_CHECKING:
    from auto_parking.service.manager import ManagerService


async def get_actor(
    credentials: HTTPBasicCredentials = sec_dep,
    manager_service: "ManagerService" = dep_manager_service,
):
    if secrets.compare_digest(credentials.username, USERNAME) and secrets.compare_digest(
        credentials.password, PASSWORD
    ):
        return {
            "type": "admin",
            "id": 0,
        }
    username_filter: ManagerFilter = ManagerFilter(username=credentials.username)
    managers = await manager_service.get(username_filter)
    manager = managers[0] if managers else None

    if not manager:
        raise HTTPException(status_code=401)

    if not verify_password(credentials.password, manager.password_hash):
        raise HTTPException(status_code=401)
    logger = logging.getLogger(__name__)
    logger.info(f"MANAGER IS {manager.username}, id - {manager.id}")
    return {
        "type": "manager",
        "id": manager.id,
    }
