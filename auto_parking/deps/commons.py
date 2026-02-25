from collections.abc import AsyncGenerator

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.core.security.actor import get_current_actor
from auto_parking.core.security.roles import (
    require_admin,
    require_manager,
)
from auto_parking.db.engine import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


depends_db = Depends(get_db)


def parse_ids(ids: str | None = Query(default=None)) -> list[int] | None:
    if ids is None:
        return None
    return [int(x) for x in ids.split(",") if x]


dep_parse_ids = Depends(parse_ids)
dep_query = Query(default=None)

dep_actor = Depends(get_current_actor)
dep_admin = Depends(require_admin)
dep_manager = Depends(require_manager)
