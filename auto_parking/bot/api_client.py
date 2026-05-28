from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class AutoParkingApiClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def login(self, username: str, password: str) -> str | None:
        try:
            async with self._client() as client:
                response = await client.post(
                    "/auth/login",
                    json={"username": username, "password": password},
                )
            if response.status_code == 401:
                return None
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        return response.json()["access_token"]

    async def get_vehicle(self, token: str, vehicle_id: int) -> dict[str, Any] | None:
        try:
            async with self._client(token) as client:
                response = await client.get(f"/vehicles/{vehicle_id}")
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        return response.json()

    async def get_vehicles_by_number_prefix(
        self,
        token: str,
        vehicle_number_prefix: str,
    ) -> list[dict[str, Any]]:
        try:
            async with self._client(token) as client:
                response = await client.get(
                    "/vehicles",
                    params={
                        "vehicle_number_prefix": vehicle_number_prefix,
                        "limit": 10,
                        "offset": 0,
                        "sort_by": "vehicle_number",
                    },
                )
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        return response.json()

    async def get_enterprises(self, token: str) -> list[dict[str, Any]]:
        try:
            async with self._client(token) as client:
                response = await client.get("/enterprises")
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        return response.json()

    async def get_enterprise_vehicles(self, token: str, enterprise_id: int) -> list[dict[str, Any]]:
        vehicles: list[dict[str, Any]] = []
        limit = 100
        offset = 0

        while True:
            try:
                async with self._client(token) as client:
                    response = await client.get(
                        "/vehicles",
                        params={
                            "enterprise_ids": str(enterprise_id),
                            "limit": limit,
                            "offset": offset,
                        },
                    )
                response.raise_for_status()
            except httpx.HTTPError:
                return []

            chunk = response.json()
            vehicles.extend(chunk)

            if len(chunk) < limit:
                return vehicles

            offset += limit

    async def get_vehicle_trips(
        self,
        *,
        token: str,
        vehicle_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[dict[str, Any]] | None:
        try:
            async with self._client(token) as client:
                response = await client.get(
                    f"/vehicles/{vehicle_id}/trips",
                    params={
                        "date_from": date_from.isoformat(),
                        "date_to": date_to.isoformat(),
                        "include_addresses": "false",
                    },
                )
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        return response.json()

    def _client(self, token: str | None = None) -> httpx.AsyncClient:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return httpx.AsyncClient(base_url=self._base_url, headers=headers, timeout=20)
