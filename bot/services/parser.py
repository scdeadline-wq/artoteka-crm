"""Парсер свободного текстового описания работы через Claude (OpenRouter).

Извлекает структурированные поля (artist, title, year, technique, размеры, цена)
из произвольного русского текста или транскрипции голосового сообщения.
"""
from __future__ import annotations

import json

import httpx

from bot.config import settings

PARSE_PROMPT = """Ты — парсер описаний произведений искусства для CRM галереи.
Получаешь свободный текст на русском (часто из голосового сообщения, могут быть ошибки распознавания).
Извлеки структурированные поля и верни ТОЛЬКО валидный JSON:

{
  "title": "Название работы или null",
  "artist_name": "Имя художника (Фамилия Имя) или null",
  "year": 2024 или null,
  "technique": "Техника как сказано (напр. 'масло, холст') или null",
  "style_period": "Стиль/направление (импрессионизм, соц-арт, абстракция и т.п.) или null",
  "width_cm": 60 или null,
  "height_cm": 80 или null,
  "sale_price": 180000 или null,
  "edition": "Тираж '12/50' или null",
  "location": "Место хранения или null",
  "description": "Если в речи есть развёрнутое описание сюжета/композиции — сюда. Иначе null.",
  "notes": "Прочее что не легло в поля выше или null"
}

Не выдумывай. Если поля нет в описании — null. Размеры могут говорить как '60 на 80', '60x80', 'шестьдесят на восемьдесят' — нормализуй в числа."""


async def parse_description(text: str) -> dict:
    """Парсит свободный текст в структурированный JSON. Все поля могут быть null."""
    if not text or not settings.openrouter_api_key:
        return {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.parse_model,
                "messages": [
                    {"role": "system", "content": PARSE_PROMPT},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 500,
            },
        )
        response.raise_for_status()
        data = response.json()

    raw = data["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
