import os
import subprocess
import sys

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_alembic_upgrade_head_builds_schema_from_scratch(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
):
    database_url = os.environ["TEST_DATABASE_URL"]
    expected_head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()

    async with integration_sessionmaker() as session:
        conn = await session.connection()
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await session.commit()

    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "JWT_SECRET_KEY": "test-secret",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    async with integration_sessionmaker() as session:
        version = await session.scalar(text("SELECT version_num FROM alembic_version"))
        vehicle_indexes = (
            await session.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'vehicle'
                      AND indexname = 'ix_vehicle_vehicle_number_prefix'
                    """
                )
            )
        ).scalars().all()

    assert version == expected_head
    assert vehicle_indexes == ["ix_vehicle_vehicle_number_prefix"]
