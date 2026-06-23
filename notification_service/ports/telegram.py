from typing import Protocol


class TelegramSender(Protocol):
    async def send_message(self, *, chat_id: int, text: str) -> None:
        pass
