from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from auto_parking.app.deps.visibility import get_visible_enterprise_ids
from auto_parking.core.domain.enums.user_role import UserRole

pytestmark = pytest.mark.asyncio


async def test_visible_enterprise_ids_skips_lookup_for_admin():
    user_service = AsyncMock()

    result = await get_visible_enterprise_ids(
        actor=SimpleNamespace(id=1, role=UserRole.admin),
        user_service=user_service,
    )

    assert result is None
    user_service.get_visible_enterprise_ids.assert_not_called()


async def test_visible_enterprise_ids_uses_lightweight_service_lookup():
    user_service = AsyncMock()
    user_service.get_visible_enterprise_ids.return_value = {10, 20}

    result = await get_visible_enterprise_ids(
        actor=SimpleNamespace(id=5, role=UserRole.manager),
        user_service=user_service,
    )

    assert result == {10, 20}
    user_service.get_visible_enterprise_ids.assert_awaited_once_with(5)


async def test_visible_enterprise_ids_raises_401_for_unknown_manager():
    user_service = AsyncMock()
    user_service.get_visible_enterprise_ids.return_value = None

    with pytest.raises(HTTPException) as err:
        await get_visible_enterprise_ids(
            actor=SimpleNamespace(id=99, role=UserRole.manager),
            user_service=user_service,
        )

    assert err.value.status_code == 401
    assert err.value.detail == "Invalid token subject"
