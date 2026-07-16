class NullCacheClient:
    async def get_text(self, key: str) -> str | None:
        return None

    async def set_text(self, key: str, value: str, *, ttl_seconds: int) -> None:
        return None

    async def delete_text(self, key: str) -> None:
        return None

    async def delete_prefix(self, prefix: str) -> None:
        return None
