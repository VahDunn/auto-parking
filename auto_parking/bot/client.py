from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from auto_parking.bot.handlers import BotReply, TelegramBotHandlers

logger = logging.getLogger(__name__)


class TelegramLongPollingClient:
    def __init__(self, token: str, handlers: TelegramBotHandlers) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._handlers = handlers
        self._offset = 0

    async def run(self) -> None:
        async with httpx.AsyncClient(timeout=35) as client:
            while True:
                try:
                    updates = await self._get_updates(client)
                except httpx.HTTPError as exc:
                    logger.warning("Telegram polling failed: %s", exc)
                    await asyncio.sleep(1)
                    continue

                for update in updates:
                    self._offset = update["update_id"] + 1
                    try:
                        await self._handle_update(client, update)
                    except Exception:
                        logger.exception(
                            "Telegram update handling failed: update_id=%s",
                            update["update_id"],
                        )

    async def _get_updates(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        response = await client.get(
            f"{self._base_url}/getUpdates",
            params={"offset": self._offset, "timeout": 30},
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("result", [])

    async def _handle_update(self, client: httpx.AsyncClient, update: dict[str, Any]) -> None:
        callback_query = update.get("callback_query")
        if callback_query:
            await self._handle_callback_query(client, callback_query)
            return

        message = update.get("message") or {}
        text = message.get("text")
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if not text or chat_id is None:
            return

        reply = await self._handlers.handle_text(chat_id=int(chat_id), text=text)
        await self._send_message(client, chat_id=int(chat_id), reply=reply)

    async def _handle_callback_query(
        self,
        client: httpx.AsyncClient,
        callback_query: dict[str, Any],
    ) -> None:
        query_id = callback_query.get("id")
        data = callback_query.get("data")
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if query_id is not None:
            await client.post(
                f"{self._base_url}/answerCallbackQuery",
                json={"callback_query_id": query_id},
            )

        if not data or chat_id is None:
            return

        reply = await self._handlers.handle_callback(chat_id=int(chat_id), data=data)
        await self._send_message(client, chat_id=int(chat_id), reply=reply)

    async def _send_message(
        self,
        client: httpx.AsyncClient,
        *,
        chat_id: int,
        reply: BotReply,
    ) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": reply.text}
        if reply.reply_markup is not None:
            payload["reply_markup"] = reply.reply_markup

        await client.post(f"{self._base_url}/sendMessage", json=payload)
