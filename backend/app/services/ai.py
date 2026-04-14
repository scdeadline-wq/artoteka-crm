"""AI-анализ фото произведений искусства через OpenRouter."""
import base64
import json
import httpx

from app.config import settings

SYSTEM_PROMPT = """Ты — эксперт-искусствовед и оценщик произведений искусства.
Тебе отправляют фотографию произведения. Проанализируй и верни JSON со следующими полями:

{
  "title": "предполагаемое название работы или null",
  "artist_name": "имя художника если узнал, или null",
  "year_estimate": "примерный год или десятилетие (напр. '1967' или '1960-е'), или null",
  "techniques": ["список техник из: Холст, масло | Картон, масло | Дерево, масло | Холст, темпера | Холст, акрил | Холст, смешанная техника | Бумага, графитный карандаш | Бумага, тушь | Бумага, тушь, перо | Бумага, акварель | Бумага, гуашь | Бумага, пастель | Бумага, сангина | Бумага, соус | Бумага, уголь | Бумага, цветные карандаши | Бумага, смешанная техника | Литография | Офорт | Ксилография | Линогравюра | Шелкография (сериграфия) | Бронза | Керамика | Фарфор | Дерево | Гипс | Фарфор, роспись | Стекло | Эмаль | Текстиль | Фотография, серебряно-желатиновая печать | Фотография, цифровая печать | Смешанная техника | Коллаж | Инсталляция"],
  "description": "краткое описание что изображено, стиль, особенности",
  "condition": "видимое состояние: отличное / хорошее / удовлетворительное / есть повреждения",
  "style_period": "стиль или период (напр. 'соцреализм', 'авангард', 'импрессионизм')",
  "estimated_price_rub": "грубая оценка рыночной стоимости в рублях или null если невозможно определить",
  "confidence": "low / medium / high — насколько ты уверен в определении"
}

Отвечай ТОЛЬКО валидным JSON, без пояснений. Если не можешь определить поле — ставь null."""


async def analyze_artwork_image(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Отправляет фото в AI и возвращает предзаполненные поля."""

    if not settings.openrouter_api_key:
        return {"error": "OpenRouter API key not configured"}

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    media_type = content_type or "image/jpeg"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}"
                                },
                            },
                            {
                                "type": "text",
                                "text": "Проанализируй это произведение искусства."
                            },
                        ],
                    },
                ],
                "max_tokens": 1000,
            },
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    # Парсим JSON из ответа (может быть обёрнут в ```json...```)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(content)
