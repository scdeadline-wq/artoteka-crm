"""Генерация фотореалистичных мокапов через OpenRouter image generation.

Используем GPT-5-image или Gemini через OpenRouter с параметром modalities: ["image", "text"].
Отправляем фото картины + промпт с описанием интерьера.
"""
import base64
from io import BytesIO

import httpx
from PIL import Image

from app.config import settings

ROOM_PROMPTS = {
    "living": "Create a photorealistic interior mockup: a modern Scandinavian living room. Light warm grey walls, a large comfortable beige linen sofa centered in front. Light oak hardwood floor, round marble coffee table, green monstera plant. The attached artwork is shown hanging on the wall above the sofa, in a slim black frame with white mat. Soft natural daylight from the left. Ultra realistic interior design photography.",
    "office": "Create a photorealistic interior mockup: a luxurious dark wood home office. Dark grey-brown painted walls, mahogany bookshelves on both sides filled with leather-bound books and silver decorative objects. Large dark wood executive desk with a leather chair in the foreground, a desk lamp. The attached artwork is shown hanging on the wall above the desk, professionally framed in a dark wood frame with gold trim and white mat. Warm amber lighting, soft shadows. Ultra realistic architectural photography, Canon EOS R5, 35mm f/2.8.",
}


async def generate_mockup(
    artwork_bytes: bytes,
    style: str = "office",
    width_cm: float | None = None,
    height_cm: float | None = None,
) -> bytes:
    """Генерирует фотореалистичный мокап через AI."""

    prompt = ROOM_PROMPTS.get(style, ROOM_PROMPTS["living"])

    # Добавляем размеры в промпт для правильного масштаба
    if width_cm and height_cm:
        size_desc = f"The artwork is {width_cm}×{height_cm} cm ({width_cm/100:.1f}×{height_cm/100:.1f} m). Scale it realistically relative to the furniture and room. "
        if max(width_cm, height_cm) < 30:
            size_desc += "This is a SMALL work, it should look compact on the wall. "
        elif max(width_cm, height_cm) > 100:
            size_desc += "This is a LARGE work, it should dominate the wall space. "
        prompt = size_desc + prompt

    # Кодируем картину
    artwork_b64 = base64.b64encode(artwork_bytes).decode("utf-8")
    img = Image.open(BytesIO(artwork_bytes))
    fmt = (img.format or "JPEG").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    mime = f"image/{fmt}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.mockup_model,
                "modalities": ["image", "text"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{artwork_b64}",
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    },
                ],
            },
        )
        response.raise_for_status()
        data = response.json()

    # Извлекаем изображение из ответа
    choice = data["choices"][0]["message"]

    # Формат OpenRouter: images в отдельном массиве
    images = choice.get("images") or []
    for img_part in images:
        if img_part.get("type") == "image_url":
            url = img_part["image_url"]["url"]
            if url.startswith("data:"):
                b64_data = url.split(",", 1)[1]
                return base64.b64decode(b64_data)
            else:
                async with httpx.AsyncClient() as dl:
                    resp = await dl.get(url)
                    return resp.content

    # Fallback: ищем в content (некоторые модели кладут туда)
    content = choice.get("content")
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "image_url":
                url = part["image_url"]["url"]
                if url.startswith("data:"):
                    b64_data = url.split(",", 1)[1]
                    return base64.b64decode(b64_data)

    raise Exception(f"No image in AI response. Keys: {list(choice.keys())}, images: {len(images)}")


def _extract_image(data: dict) -> bytes:
    """Извлекает изображение из ответа OpenRouter."""
    choice = data["choices"][0]["message"]
    for img_part in choice.get("images") or []:
        if img_part.get("type") == "image_url":
            url = img_part["image_url"]["url"]
            if url.startswith("data:"):
                return base64.b64decode(url.split(",", 1)[1])
    content = choice.get("content")
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "image_url":
                url = part["image_url"]["url"]
                if url.startswith("data:"):
                    return base64.b64decode(url.split(",", 1)[1])
    raise Exception("No image in AI response")


async def generate_custom_mockup(
    room_bytes: bytes,
    artwork_bytes: bytes,
    width_cm: float | None = None,
    height_cm: float | None = None,
) -> bytes:
    """Персональный мокап: фото комнаты клиента + картина на стене."""

    room_b64 = base64.b64encode(room_bytes).decode("utf-8")
    artwork_b64 = base64.b64encode(artwork_bytes).decode("utf-8")

    room_img = Image.open(BytesIO(room_bytes))
    room_mime = f"image/{(room_img.format or 'JPEG').lower().replace('jpg','jpeg')}"

    art_img = Image.open(BytesIO(artwork_bytes))
    art_mime = f"image/{(art_img.format or 'JPEG').lower().replace('jpg','jpeg')}"

    size_hint = ""
    if width_cm and height_cm:
        size_hint = f"The artwork is {width_cm}×{height_cm} cm. Scale it realistically relative to the room. "

    prompt = (
        f"This is a photo of a client's room (first image). "
        f"Place the artwork (second image) on the most suitable empty wall in this room. "
        f"{size_hint}"
        f"The artwork should be professionally framed, properly scaled to the room proportions, "
        f"and look like a real photo — matching lighting, perspective, and color temperature of the room. "
        f"Keep the room exactly as-is, only add the framed artwork on the wall. "
        f"Photorealistic result, no distortion of the original room."
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.mockup_model,
                "modalities": ["image", "text"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{room_mime};base64,{room_b64}"},
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{art_mime};base64,{artwork_b64}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    },
                ],
            },
        )
        response.raise_for_status()
        return _extract_image(response.json())
