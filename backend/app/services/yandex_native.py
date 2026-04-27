"""Native Яндекс реверс-поиск через прямую загрузку файла.

В отличие от SearchAPI.io (URL-based, не работает для неиндексированных URL),
этот клиент имитирует drag-and-drop из UI yandex.com/images:
1. POST файла на /images/search?rpt=imageview&format=json — получаем cbir_id
2. GET /images/search?cbir_id=X&rpt=imageview&cbir_page=sites — HTML со списком сайтов
3. Парсим CbirSites-Item блоки

Лучше всего работает с российского IP (наш VPS). При SmartCaptcha
возвращает пустой список — fallback на Google Lens в `web_search.py`.
"""
import json

import httpx
from bs4 import BeautifulSoup

UPLOAD_URL = "https://yandex.com/images/search"
SITES_URL = "https://yandex.com/images/search"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
RENDER_REQUEST = json.dumps({"blocks": [{"block": "b-page_type_search-by-image__link"}]})
TOP_RESULTS = 10


async def yandex_search_by_image(image_bytes: bytes, content_type: str = "image/jpeg") -> list[dict]:
    """Реверс-поиск по файлу через нативный flow Яндекса."""
    headers = {"User-Agent": USER_AGENT, "Referer": "https://yandex.com/images/"}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
        cbir_id = await _upload_and_get_cbir_id(client, image_bytes, content_type)
        if not cbir_id:
            return []

        return await _fetch_sites(client, cbir_id)


async def _upload_and_get_cbir_id(client: httpx.AsyncClient, image_bytes: bytes, content_type: str) -> str | None:
    files = {"upfile": ("blob", image_bytes, content_type or "image/jpeg")}
    params = {"rpt": "imageview", "format": "json", "request": RENDER_REQUEST}

    try:
        response = await client.post(UPLOAD_URL, params=params, files=files)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None

    blocks = data.get("blocks") or []
    if not blocks:
        return None
    return blocks[0].get("params", {}).get("cbirId")


async def _fetch_sites(client: httpx.AsyncClient, cbir_id: str) -> list[dict]:
    params = {"cbir_id": cbir_id, "rpt": "imageview", "cbir_page": "sites"}
    try:
        response = await client.get(SITES_URL, params=params)
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    if "captcha" in response.text.lower() and "showcaptcha" in response.text.lower():
        return []

    return _parse_sites(response.text)


def _parse_sites(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("li.CbirSites-Item")
    results = []

    for item in items[:TOP_RESULTS]:
        title_link = item.select_one(".CbirSites-ItemTitle a")
        domain_link = item.select_one(".CbirSites-ItemDomain")
        description = item.select_one(".CbirSites-ItemDescription")

        link = title_link.get("href") if title_link else None
        title = title_link.get_text(strip=True) if title_link else None
        source = domain_link.get_text(strip=True) if domain_link else None
        snippet = description.get_text(strip=True) if description else None

        if not (title or link):
            continue

        results.append({
            "title": title,
            "source": source,
            "link": link,
            "snippet": snippet,
        })

    return results
