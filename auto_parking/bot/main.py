from __future__ import annotations

import asyncio

from auto_parking.bot.api_client import AutoParkingApiClient
from auto_parking.bot.client import TelegramLongPollingClient
from auto_parking.bot.handlers import TelegramBotHandlers
from auto_parking.bot.service import BotService
from auto_parking.core.config import settings
from auto_parking.core.logger import setup_logging
from auto_parking.deps.cache import get_cache_client


async def main() -> None:
    setup_logging()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run Telegram bot")

    api_client = AutoParkingApiClient(settings.bot_api_base_url)
    handlers = TelegramBotHandlers(
        service=BotService(
            api_client,
            cache=get_cache_client(),
            cache_ttl_seconds=settings.bot_summary_cache_ttl_seconds,
        )
    )
    await TelegramLongPollingClient(settings.telegram_bot_token, handlers).run()


if __name__ == "__main__":
    asyncio.run(main())
