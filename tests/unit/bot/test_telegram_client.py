from unittest.mock import AsyncMock

import httpx
import pytest

from auto_parking.bot.client import TelegramLongPollingClient

pytestmark = pytest.mark.asyncio


class StopPolling(BaseException):
    pass


class FakeAsyncClientContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


async def test_telegram_client_retries_after_polling_http_error(monkeypatch):
    polling_client = TelegramLongPollingClient("token", AsyncMock())
    polling_client._get_updates = AsyncMock(
        side_effect=[httpx.ReadTimeout("slow response"), StopPolling]
    )
    sleep = AsyncMock()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeAsyncClientContext())
    monkeypatch.setattr("auto_parking.bot.client.asyncio.sleep", sleep)

    with pytest.raises(StopPolling):
        await polling_client.run()

    sleep.assert_awaited_once_with(1)
    assert polling_client._get_updates.await_count == 2


async def test_telegram_client_continues_after_update_handling_error(monkeypatch):
    polling_client = TelegramLongPollingClient("token", AsyncMock())
    polling_client._get_updates = AsyncMock(
        side_effect=[
            [{"update_id": 1}, {"update_id": 2}],
            StopPolling,
        ]
    )
    polling_client._handle_update = AsyncMock(side_effect=[RuntimeError("boom"), None])

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeAsyncClientContext())

    with pytest.raises(StopPolling):
        await polling_client.run()

    assert polling_client._handle_update.await_count == 2
    assert polling_client._offset == 3
