from functools import lru_cache

from redis.asyncio import Redis

from auto_parking.core.config import settings
from auto_parking.integrations.cache import NullCacheClient, RedisCacheClient
from auto_parking.ports.cache import CacheClient


@lru_cache
def get_cache_client() -> CacheClient:
    if not settings.redis_url:
        return NullCacheClient()

    redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    return RedisCacheClient(redis)
