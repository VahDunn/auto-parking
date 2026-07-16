from redis.asyncio import Redis


class RedisCacheClient:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_text(self, key: str) -> str | None:
        value = await self._redis.get(key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    async def set_text(self, key: str, value: str, *, ttl_seconds: int) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)

    async def delete_text(self, key: str) -> None:
        await self._redis.delete(key)

    async def delete_prefix(self, prefix: str) -> None:
        keys: list[str] = []
        async for key in self._redis.scan_iter(match=f"{prefix}*", count=100):
            keys.append(key)

        if keys:
            await self._redis.delete(*keys)
