import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.db.models import Enterprise

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def seed_enterprise(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> Enterprise:
    async with sessionmaker() as session:
        enterprise = Enterprise(
            name="Disposable enterprise",
            settlement="Moscow",
            timezone="Europe/Moscow",
        )
        session.add(enterprise)
        await session.commit()
        await session.refresh(enterprise)
        return enterprise


async def test_enterprise_delete_removes_enterprise_from_database(
    integration_client,
    integration_sessionmaker,
):
    enterprise = await seed_enterprise(integration_sessionmaker)

    get_response = await integration_client.get(f"/api/enterprises/{enterprise.id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Disposable enterprise"

    delete_response = await integration_client.delete(f"/api/enterprises/{enterprise.id}")
    assert delete_response.status_code == 204

    async with integration_sessionmaker() as session:
        persisted = await session.get(Enterprise, enterprise.id)

    assert persisted is None

    get_deleted_response = await integration_client.get(f"/api/enterprises/{enterprise.id}")
    assert get_deleted_response.status_code == 404
