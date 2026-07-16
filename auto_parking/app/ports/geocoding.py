from typing import Protocol


class ReverseGeocoder(Protocol):
    async def reverse_geocode(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> str | None:
        pass
