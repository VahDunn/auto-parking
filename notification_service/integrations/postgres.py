from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine_and_session_factory(
    database_url: str,
    *,
    debug: bool = False,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        database_url,
        echo=debug,
        future=True,
    )
    return (
        engine,
        async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            class_=AsyncSession,
        ),
    )


class PostgresManagerLookup:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def manager_ids_for_enterprise(self, enterprise_id: int) -> Sequence[int]:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT u.id
                    FROM "user" AS u
                    JOIN user_enterprise AS ue ON ue.user_id = u.id
                    WHERE ue.enterprise_id = :enterprise_id
                      AND u.role = 'manager'
                    ORDER BY u.id
                    """
                ),
                {"enterprise_id": enterprise_id},
            )
            return [int(user_id) for user_id in result.scalars().all()]
