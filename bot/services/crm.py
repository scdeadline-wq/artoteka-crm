"""HTTP-клиент к ArtSpace CRM API.

Логинится один раз при первом запросе, кеширует JWT, при 401 — релогин.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from bot.config import settings

JWT_REFRESH_BEFORE_EXPIRY = 60  # секунд


class CRMClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.crm_base_url, timeout=120.0)
        self._token: str | None = None
        self._token_exp: float = 0
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._client.aclose()

    async def _ensure_token(self) -> str:
        async with self._lock:
            if self._token and time.time() < self._token_exp - JWT_REFRESH_BEFORE_EXPIRY:
                return self._token

            response = await self._client.post(
                "/auth/login/",
                json={"email": settings.crm_user_email, "password": settings.crm_user_password},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            # JWT по умолчанию живёт 24 часа в CRM (jwt_expire_minutes=1440)
            self._token_exp = time.time() + 1440 * 60
            return self._token

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        token = await self._ensure_token()
        headers = kwargs.pop("headers", {}) or {}
        headers["Authorization"] = f"Bearer {token}"
        response = await self._client.request(method, url, headers=headers, **kwargs)
        if response.status_code == 401:
            self._token = None
            token = await self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            response = await self._client.request(method, url, headers=headers, **kwargs)
        return response

    async def analyze_image(self, image_bytes: bytes, filename: str = "photo.jpg") -> dict[str, Any]:
        files = {"file": (filename, image_bytes, "image/jpeg")}
        response = await self._request("POST", "/artworks/analyze-image/", files=files)
        response.raise_for_status()
        return response.json()

    async def search_artworks(self, query: str | None = None) -> list[dict[str, Any]]:
        params = {"q": query} if query else {}
        response = await self._request("GET", "/artworks/", params=params)
        response.raise_for_status()
        return response.json()

    async def get_artwork(self, artwork_id: int) -> dict[str, Any]:
        response = await self._request("GET", f"/artworks/{artwork_id}/")
        response.raise_for_status()
        return response.json()

    async def create_artwork(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/artworks/", json=payload)
        response.raise_for_status()
        return response.json()

    async def upload_artwork_image(self, artwork_id: int, image_bytes: bytes, primary: bool = True) -> dict[str, Any]:
        files = {"file": ("photo.jpg", image_bytes, "image/jpeg")}
        response = await self._request(
            "POST",
            f"/artworks/{artwork_id}/images/",
            files=files,
            params={"is_primary": str(primary).lower()},
        )
        response.raise_for_status()
        return response.json()

    async def update_artwork_status(self, artwork_id: int, status: str) -> dict[str, Any]:
        response = await self._request(
            "PATCH",
            f"/artworks/{artwork_id}/status/",
            json={"status": status},
        )
        response.raise_for_status()
        return response.json()

    async def list_artists(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/artists/")
        response.raise_for_status()
        return response.json()

    async def create_artist(self, name_ru: str, name_en: str | None = None) -> dict[str, Any]:
        payload = {"name_ru": name_ru, "name_en": name_en}
        response = await self._request("POST", "/artists/", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_clients(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/clients/")
        response.raise_for_status()
        return response.json()

    async def create_client(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/clients/", json=payload)
        response.raise_for_status()
        return response.json()

    async def download_image(self, image_url: str) -> bytes:
        """Скачивает байты из CRM по относительному /images/-пути.

        Вход — то, что лежит в Image.url или primary_image (например
        '/images/artworks/12/abc.jpg'). Идём через внутренний docker URL
        backend, поэтому фаервол/гео-блоки не страшны.
        """
        path = image_url.lstrip("/")
        token = await self._ensure_token()
        response = await self._client.get(
            f"/{path}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.content

    async def list_techniques(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/techniques/")
        response.raise_for_status()
        return response.json()

    async def create_sale(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/sales/", json=payload)
        response.raise_for_status()
        return response.json()


crm = CRMClient()
