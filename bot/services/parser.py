"""Парсер свободного текстового описания работы через LLM (MixRoute).

Извлекает структурированные поля (artist, title, year, technique, размеры, цена)
из произвольного русского текста или транскрипции голосового сообщения.
"""
from __future__ import annotations

import json

from bot.config import settings
from bot.services import llm

PARSE_PROMPT = """Ты — парсер описаний произведений искусства для CRM галереи.
Получаешь свободный текст на русском (часто из голосового сообщения, могут быть ошибки распознавания).
Извлеки структурированные поля и верни ТОЛЬКО валидный JSON:

{
  "title": "Название работы или null",
  "artist_name": "Имя художника (Фамилия Имя) или null",
  "year": "Год как сказано: '2024', '2016-2017', '2000-е' или null",
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

Не выдумывай. Если поля нет в описании — null. Размеры могут говорить как '80 на 60', '80x60', 'восемьдесят на шестьдесят' — нормализуй в числа. Принято писать высота × ширина: первое число — height_cm, второе — width_cm."""


async def parse_description(text: str) -> dict:
    """Парсит свободный текст в структурированный JSON. Все поля могут быть null."""
    if not text or not settings.ai_api_key:
        return {}

    raw = await llm.chat({
        "model": settings.parse_model,
        "messages": [
            {"role": "system", "content": PARSE_PROMPT},
            {"role": "user", "content": text},
        ],
        "max_tokens": 1500,
        "reasoning_effort": "none",
    }, timeout=30.0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
