"""Реверс-поиск изображений через Яндекс (SearchAPI.io)."""
import hashlib
import json
from io import BytesIO

import boto3
import httpx
import redis.asyncio as redis_async
from PIL import Image

from app.config import settings

CACHE_TTL_SECONDS = 7 * 24 * 3600
TEMP_PREFIX = "temp/analyze"
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
TOP_RESULTS = 5

# Форматы, которые Яндекс умеет открывать при реверс-поиске
SEARCH_SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}


async def search_artwork_by_image(image_bytes: bytes) -> list[dict]:
    """Возвращает список результатов реверс-поиска Яндекса.

    Каждый элемент: {title, source, link, snippet}.
    Пустой список если ключ не настроен или ничего не найдено.
    """
    if not settings.searchapi_key:
        return []

    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cache_key = f"yandex_search:{image_hash}"

    redis_client = redis_async.from_url(settings.redis_url, decode_responses=True)
    try:
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)

        image_url = _upload_temp_image(image_bytes, image_hash)
        results = await _call_searchapi(image_url)

        await redis_client.set(cache_key, json.dumps(results, ensure_ascii=False), ex=CACHE_TTL_SECONDS)
        return results
    finally:
        await redis_client.aclose()


def _upload_temp_image(image_bytes: bytes, image_hash: str) -> str:
    """Заливает байты в MinIO без перекодирования (perceptual hash важен для реверс-поиска).

    HEIC и другие неподдерживаемые форматы конвертируются в JPEG quality=98.
    Известные форматы (JPEG, PNG, WEBP) идут as-is.
    """
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
    """Возвращает (bytes, extension, content_type) для загрузки в MinIO."""
    img = Image.open(BytesIO(image_bytes))
    fmt = (img.format or "").upper()

    if fmt in SEARCH_SUPPORTED_FORMATS:
        ext = "jpg" if fmt == "JPEG" else fmt.lower()
        return image_bytes, ext, f"image/{fmt.lower()}"

    # HEIC/HEIF и прочая экзотика — конвертируем в JPEG с минимальной потерей
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=98)
    return buf.getvalue(), "jpg", "image/jpeg"


async def _call_searchapi(image_url: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            SEARCHAPI_URL,
            params={
                "engine": "yandex_reverse_image",
                "url": image_url,
                "api_key": settings.searchapi_key,
            },
        )
        response.raise_for_status()
        data = response.json()

    visual_matches = data.get("visual_matches") or []
    return [
        {
            "title": m.get("title"),
            "source": m.get("source"),
            "link": m.get("link"),
            "snippet": m.get("snippet"),
        }
        for m in visual_matches[:TOP_RESULTS]
    ]
