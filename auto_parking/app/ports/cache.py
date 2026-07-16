from typing import Protocol


class CacheClient(Protocol):
    async def get_text(self, key: str) -> str | None:
        pass

    async def set_text(self, key: str, value: str, *, ttl_seconds: int) -> None:
        pass

    async def delete_text(self, key: str) -> None:
        pass

    async def delete_prefix(self, prefix: str) -> None:
        pass
