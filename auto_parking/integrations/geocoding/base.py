from __future__ import annotations

from abc import ABC, abstractmethod


class ReverseGeocoder(ABC):
    @abstractmethod
    async def reverse_geocode(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> str | None:
        raise NotImplementedError
