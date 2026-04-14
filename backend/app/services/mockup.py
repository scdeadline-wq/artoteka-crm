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
    "office": "Create a photorealistic interior mockup: a luxurious dark wood home office. Dark grey-brown painted walls, mahogany bookshelves on both sides filled with leather-bound books and silver decorative objects. Large dark wood executive desk with a leather chair in the foreground, a desk lamp. The attached artwork is shown hanging on the wall above the desk, professionally framed in a dark wood frame with gold trim and white mat. Warm amber lighting, soft shadows. Ultra realistic architectural photography, Canon EOS R5, 35mm f/2.8.",
    "living": "Create a photorealistic interior mockup: a modern Scandinavian living room. Light warm grey walls, a large comfortable beige linen sofa centered in front. Light oak hardwood floor, round marble coffee table, green monstera plant. The attached artwork is shown hanging on the wall above the sofa, in a slim black frame with white mat. Soft natural daylight from the left. Ultra realistic interior design photography.",
    "bedroom": "Create a photorealistic interior mockup: an elegant modern bedroom. Soft sage green walls, luxurious upholstered headboard in cream linen, white cotton bedding with textured throw pillows. Oak bedside tables with ceramic lamps. The attached artwork is shown hanging above the headboard, in a light oak frame with linen mat. Warm cozy evening lighting. Ultra realistic photography.",
    "gallery": "Create a photorealistic interior mockup: a contemporary art gallery. Clean white walls, polished light concrete floor, professional track lighting casting focused light. Minimal oak bench in the foreground. The attached artwork is shown hanging centered on the main wall in a minimal black frame. Museum-quality directional lighting. Ultra realistic architectural photography.",
}


async def generate_mockup(artwork_bytes: bytes, style: str = "office") -> bytes:
    """Генерирует фотореалистичный мокап через AI."""

    prompt = ROOM_PROMPTS.get(style, ROOM_PROMPTS["living"])

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
