from typing import Protocol


class TelegramSessionRegistry(Protocol):
    async def get_telegram_chat_id(self, *, user_id: int) -> int | None:
        pass
