"""Голос → структурированные поля одним вызовом через OpenRouter Voxtral.

Заменяет Whisper + отдельный парсер: модель сама распознаёт речь и
сразу извлекает JSON. Telegram присылает голосовые в OGG/Opus —
voxtral принимает ogg напрямую (gpt-audio-mini требовал wav/mp3).
"""
from __future__ import annotations

import base64
import json

import httpx

from bot.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
AUDIO_MODEL = "mistralai/voxtral-small-24b-2507"

PROMPT = """Это голосовое описание произведения искусства из CRM галереи.
Распознай речь на русском и извлеки структурированные поля. Верни ТОЛЬКО валидный JSON:

{
  "transcript": "Дословная транскрипция голосового",
  "title": "Название работы или null",
  "artist_name": "Имя художника (Фамилия Имя) или null",
  "year": 2024 или null,
  "technique": "Техника как сказана ('масло, холст', 'бумага, акварель' и т.п.) или null",
  "style_period": "Стиль/направление (импрессионизм, абстракция, соц-арт и т.п.) или null",
  "width_cm": 60 или null,
  "height_cm": 80 или null,
  "sale_price": 180000 или null,
  "edition": "Тираж '12/50' или null",
  "location": "Место хранения или null",
  "description": "Развёрнутое описание сюжета/композиции если есть или null",
  "notes": "Прочее или null"
}

Не выдумывай. Размеры могут говорить как '60 на 80', '60x80', 'шестьдесят на восемьдесят' — нормализуй в числа."""


async def parse_voice(audio_bytes: bytes, audio_format: str = "ogg") -> dict:
    """Один вызов в gpt-audio-mini: распознаёт + парсит → JSON."""
    if not settings.openrouter_api_key:
        return {}

    audio_b64 = base64.b64encode(audio_bytes).decode()

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": AUDIO_MODEL,
                "modalities": ["text"],
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "input_audio": {"data": audio_b64, "format": audio_format}},
                        {"type": "text", "text": PROMPT},
                    ],
                }],
                "max_tokens": 800,
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
        return {"transcript": raw}
