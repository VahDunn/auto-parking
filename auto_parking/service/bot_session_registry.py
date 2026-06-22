import json

from auto_parking.ports.cache import CacheClient


class BotSessionRegistry:
    def __init__(
        self,
        cache: CacheClient,
        *,
        ttl_seconds: int,
    ) -> None:
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def bind_telegram_chat(
        self,
        *,
        user_id: int,
        chat_id: int,
        username: str,
        role: str,
    ) -> None:
        await self._cache.set_text(
            self._key(user_id),
            json.dumps(
                {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "username": username,
                    "role": role,
                },
                ensure_ascii=False,
            ),
            ttl_seconds=self._ttl_seconds,
        )

    async def get_telegram_chat_id(self, *, user_id: int) -> int | None:
        raw = await self._cache.get_text(self._key(user_id))
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return int(data["chat_id"])
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            return None

    @staticmethod
    def _key(user_id: int) -> str:
        return f"bot:telegram:user:{user_id}"
