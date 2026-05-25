from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.core.domain.enums import UserRole
from auto_parking.core.errors import ConflictError, ForbiddenError, NotFoundError
from auto_parking.filter import EnterpriseFilter
from auto_parking.service.enterprise import EnterpriseService

pytestmark = pytest.mark.asyncio


def enterprise_orm():
    return SimpleNamespace(
        id=10,
        name="Enterprise",
        settlement="Moscow",
        timezone="Europe/Moscow",
        vehicles=[SimpleNamespace(id=1)],
        drivers=[SimpleNamespace(id=11)],
        users=[
            SimpleNamespace(id=5, role=UserRole.manager),
            SimpleNamespace(id=6, role=UserRole.user),
        ],
    )


async def test_enterprise_service_get_maps_domain_model():
    repo = AsyncMock()
    repo.get.return_value = [enterprise_orm()]
    service = EnterpriseService(repo)

    result = await service.get(EnterpriseFilter(ids=[10]))

    assert result[0].id == 10
    assert result[0].vehicles == [1]
    assert result[0].drivers == [11]
    assert result[0].managers == [5]


async def test_enterprise_service_get_by_id_raises_not_found():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = EnterpriseService(repo)

    with pytest.raises(NotFoundError):
        await service.get_by_id(999)


async def test_enterprise_service_delete_allows_admin():
    repo = AsyncMock()
    repo.get_by_id.return_value = enterprise_orm()
    repo.delete.return_value = True
    service = EnterpriseService(repo)

    await service.delete(10, SimpleNamespace(id=1, role=UserRole.admin))

    repo.delete.assert_awaited_once_with(10)
    repo.is_user_linked.assert_not_called()


async def test_enterprise_service_delete_rejects_unlinked_manager():
    repo = AsyncMock()
    repo.get_by_id.return_value = enterprise_orm()
    repo.is_user_linked.return_value = False
    service = EnterpriseService(repo)

    with pytest.raises(ForbiddenError):
        await service.delete(10, SimpleNamespace(id=5, role=UserRole.manager))


async def test_enterprise_service_delete_rejects_shared_enterprise():
    repo = AsyncMock()
    repo.get_by_id.return_value = enterprise_orm()
    repo.is_user_linked.return_value = True
    repo.count_enterprise_managers.return_value = 2
    service = EnterpriseService(repo)

    with pytest.raises(ConflictError):
        await service.delete(10, SimpleNamespace(id=5, role=UserRole.manager))
