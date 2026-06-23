import json

from redis.asyncio import Redis


class RedisTelegramSessionRegistry:
    def __init__(self, redis_url: str | None) -> None:
        self._redis = (
            Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            if redis_url
            else None
        )

    async def get_telegram_chat_id(self, *, user_id: int) -> int | None:
        if self._redis is None:
            return None

        raw = await self._redis.get(self._key(user_id))
        if raw is None:
            return None

        try:
            data = json.loads(raw)
            return int(data["chat_id"])
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            return None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    @staticmethod
    def _key(user_id: int) -> str:
        return f"bot:telegram:user:{user_id}"
