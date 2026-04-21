from typing import Any

import httpx


class GeoapifyGeocoder:
    BASE_URL = "https://api.geoapify.com/v1/geocode/reverse"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def reverse_geocode(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> str | None:
        params = {
            "lat": latitude,
            "lon": longitude,
            "apiKey": self._api_key,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        features = data.get("features") or []
        if not features:
            return None

        properties = features[0].get("properties") or {}
        formatted = properties.get("formatted")

        if isinstance(formatted, str) and formatted.strip():
            return formatted.strip()

        return None
