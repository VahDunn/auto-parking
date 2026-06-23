import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramBotSender:
    def __init__(self, token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, *, chat_id: int, text: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{self._base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.warning("Telegram notification send failed: chat_id=%s", chat_id, exc_info=True)
