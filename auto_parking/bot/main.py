from __future__ import annotations

import asyncio

from auto_parking.bot.api_client import AutoParkingApiClient
from auto_parking.bot.client import TelegramLongPollingClient
from auto_parking.bot.handlers import TelegramBotHandlers
from auto_parking.bot.service import BotService
from auto_parking.core.config import settings


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run Telegram bot")

    api_client = AutoParkingApiClient(settings.bot_api_base_url)
    handlers = TelegramBotHandlers(service=BotService(api_client))
    await TelegramLongPollingClient(settings.telegram_bot_token, handlers).run()


if __name__ == "__main__":
    asyncio.run(main())
