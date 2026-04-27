"""Реверс-поиск изображений: Google Lens + Native Yandex.

Два движка работают параллельно:
- Google Lens (через SearchAPI.io по URL) — известные мировые работы,
  perceptual hash search.
- Native Yandex (прямая загрузка файла) — русский арт-контекст,
  artchive.ru / gallerix.ru / ru-аукционы.

Результаты объединяются с дедупом по ссылке и отфильтровываются от
коммерческого мусора (Amazon, AliExpress, Pinterest и т.п.).
"""
import asyncio
import hashlib
import json
from io import BytesIO
from urllib.parse import urlparse

import boto3
import httpx
import redis.asyncio as redis_async
from PIL import Image

from app.config import settings
from app.services.yandex_native import yandex_search_by_image

CACHE_TTL_SECONDS = 7 * 24 * 3600
TEMP_PREFIX = "temp/analyze"
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
SEARCH_ENGINE = "google_lens"
TOP_RESULTS_PER_ENGINE = 10
FINAL_TOP_RESULTS = 8

SEARCH_SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}

# Доменные суффиксы которые не несут пользы для атрибуции (постеры/принты/маркетплейсы)
NOISE_DOMAINS = {
    "amazon.com", "amazon.de", "amazon.co.uk", "amazon.fr", "amazon.it",
    "ebay.com", "ebay.co.uk", "ebay.de",
    "aliexpress.com", "aliexpress.ru",
    "etsy.com",
    "pinterest.com", "pinterest.ru", "pinterest.co.uk",
    "ozon.ru", "wildberries.ru",
    "redbubble.com", "society6.com", "zazzle.com", "fineartamerica.com",
    "shutterstock.com", "istockphoto.com", "alamy.com", "dreamstime.com",
}


async def search_artwork_by_image(image_bytes: bytes) -> list[dict]:
    """Возвращает объединённый список результатов от Google Lens + Yandex.

    Каждый элемент: {title, source, link, snippet, engine}.
    Пустой список если оба движка ничего не нашли.
    """
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cache_key = f"image_search:{image_hash}"

    redis_client = redis_async.from_url(settings.redis_url, decode_responses=True)
    try:
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)

        google_task = _google_lens_search(image_bytes, image_hash)
        yandex_task = yandex_search_by_image(image_bytes)
        google_results, yandex_results = await asyncio.gather(
            google_task, yandex_task, return_exceptions=True
        )

        google_list = google_results if isinstance(google_results, list) else []
        yandex_list = yandex_results if isinstance(yandex_results, list) else []

        merged = _merge_and_filter(google_list, yandex_list)

        await redis_client.set(cache_key, json.dumps(merged, ensure_ascii=False), ex=CACHE_TTL_SECONDS)
        return merged
    finally:
        await redis_client.aclose()


async def _google_lens_search(image_bytes: bytes, image_hash: str) -> list[dict]:
    if not settings.searchapi_key:
        return []
    image_url = _upload_temp_image(image_bytes, image_hash)
    return await _call_searchapi(image_url)


def _upload_temp_image(image_bytes: bytes, image_hash: str) -> str:
    body, ext, content_type = _prepare_for_search(image_bytes)
    key = f"{TEMP_PREFIX}/{image_hash}.{ext}"

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    return f"{settings.public_base_url}/images/{key}"


def _prepare_for_search(image_bytes: bytes) -> tuple[bytes, str, str]:
    img = Image.open(BytesIO(image_bytes))
    fmt = (img.format or "").upper()

    if fmt in SEARCH_SUPPORTED_FORMATS:
        ext = "jpg" if fmt == "JPEG" else fmt.lower()
        return image_bytes, ext, f"image/{fmt.lower()}"

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=98)
    return buf.getvalue(), "jpg", "image/jpeg"


async def _call_searchapi(image_url: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                SEARCHAPI_URL,
                params={
                    "engine": SEARCH_ENGINE,
                    "url": image_url,
                    "api_key": settings.searchapi_key,
                },
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            return []

    visual_matches = data.get("visual_matches") or []
    return [
        {
            "title": m.get("title"),
            "source": m.get("source"),
            "link": m.get("link"),
            "snippet": m.get("snippet"),
        }
        for m in visual_matches[:TOP_RESULTS_PER_ENGINE]
    ]


def _merge_and_filter(google: list[dict], yandex: list[dict]) -> list[dict]:
    """Объединяет результаты, фильтрует мусор, дедуплицирует по домену+title.

    Сначала идёт Yandex (приоритет русским источникам), потом Google.
    """
    seen = set()
    merged = []

    for engine_name, results in [("yandex", yandex), ("google", google)]:
        for r in results:
            link = r.get("link") or ""
            title = (r.get("title") or "").strip()
            domain = _extract_domain(link)

            if not (link or title):
                continue
            if domain in NOISE_DOMAINS:
                continue

            dedupe_key = (domain, title.lower()[:80])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            merged.append({**r, "engine": engine_name})

            if len(merged) >= FINAL_TOP_RESULTS:
                return merged

    return merged


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""
