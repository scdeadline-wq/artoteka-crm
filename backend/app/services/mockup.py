"""Генерация фотореалистичных мокапов через AI image generation (OpenRouter)."""
import base64
from io import BytesIO

import httpx
from PIL import Image

from app.config import settings

ROOM_PROMPTS = {
    "office": "Photorealistic interior photograph of a luxurious dark wood home office. Dark grey-brown painted walls, mahogany bookshelves on both sides filled with leather-bound books, silver decorative objects, and small framed photos. Large dark wood executive desk with a leather chair, desk lamp, leather accessories. The framed artwork shown in the reference image is hanging centered on the wall above the desk, with a gold-trimmed dark wood frame and white mat. Warm amber ambient lighting, soft shadows. Shot with Canon EOS R5, 35mm lens, f/2.8. Ultra realistic, 4K quality architectural photography.",
    "living": "Photorealistic interior photograph of a modern Scandinavian living room. Light warm grey walls, large comfortable beige linen sofa centered below the wall. Light oak hardwood floor, round marble coffee table, green monstera plant in a ceramic pot. The framed artwork shown in the reference image is hanging centered on the wall above the sofa, with a slim black frame and white mat. Soft natural daylight from large windows on the left. Shot with Sony A7IV, 28mm lens. Ultra realistic, 4K interior design photography.",
    "bedroom": "Photorealistic interior photograph of an elegant modern bedroom. Soft sage green walls, luxurious upholstered headboard in cream linen fabric, white cotton bedding with textured throw pillows. Oak bedside tables with ceramic table lamps. The framed artwork shown in the reference image is hanging centered on the wall above the headboard, with a light oak frame and linen mat. Warm cozy evening lighting, soft shadows. Shot with Nikon Z7, 35mm lens. Ultra realistic, 4K quality.",
    "gallery": "Photorealistic interior photograph of a contemporary art gallery space. Clean white walls, polished light concrete floor, professional track lighting on the ceiling casting focused light on the wall. Minimal oak bench in the foreground. The framed artwork shown in the reference image is hanging centered on the main wall, with a minimal black frame. Museum-quality directional lighting creating subtle shadows. Shot with Hasselblad X2D, 45mm lens. Ultra realistic, 4K architectural photography.",
}


async def generate_mockup(artwork_bytes: bytes, style: str = "office") -> bytes:
    """Генерирует фотореалистичный мокап через AI image generation."""

    prompt = ROOM_PROMPTS.get(style, ROOM_PROMPTS["living"])

    # Кодируем картину в base64
    artwork_b64 = base64.b64encode(artwork_bytes).decode("utf-8")

    # Определяем формат
    img = Image.open(BytesIO(artwork_bytes))
    fmt = img.format or "JPEG"
    mime = f"image/{fmt.lower()}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.mockup_model,
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
                                "text": f"Generate a photorealistic interior mockup image showing this exact artwork framed and hanging on the wall. {prompt}",
                            },
                        ],
                    },
                ],
            },
        )
        response.raise_for_status()
        data = response.json()

    # Ищем сгенерированное изображение в ответе
    choice = data["choices"][0]["message"]

    # Некоторые модели возвращают изображение в content как multimodal
    if isinstance(choice.get("content"), list):
        for part in choice["content"]:
            if part.get("type") == "image_url":
                url = part["image_url"]["url"]
                if url.startswith("data:"):
                    # base64 inline
                    b64_data = url.split(",", 1)[1]
                    return base64.b64decode(b64_data)
                else:
                    # URL
                    async with httpx.AsyncClient() as dl:
                        img_resp = await dl.get(url)
                        return img_resp.content

    # Fallback: если модель вернула URL в тексте
    content = choice.get("content", "")
    if isinstance(content, str) and "http" in content:
        import re
        urls = re.findall(r'https?://[^\s\)"\']+\.(?:png|jpg|jpeg|webp)', content)
        if urls:
            async with httpx.AsyncClient() as dl:
                img_resp = await dl.get(urls[0])
                return img_resp.content

    raise Exception(f"No image in AI response. Content: {str(content)[:200]}")
