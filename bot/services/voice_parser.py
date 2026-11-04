"""Голос → структурированные поля одним вызовом (MixRoute, LLM_VOICE_MODEL).

Модель сама распознаёт речь и сразу извлекает JSON. Telegram присылает
голосовые в OGG/Opus, а MixRoute для Gemini принимает только mp3/wav
(ogg отвечает 500 «mime type is not supported») — перекодируем ffmpeg в mp3.
"""
from __future__ import annotations

import asyncio
import base64
import json

from bot.config import settings
from bot.services import llm


PROMPT = """Это голосовое описание произведения искусства из CRM галереи.
Распознай речь на русском и извлеки структурированные поля. Верни ТОЛЬКО валидный JSON:

{
  "transcript": "Дословная транскрипция голосового",
  "title": "Название работы или null",
  "artist_name": "Имя художника (Фамилия Имя) или null",
  "year": "Год как сказано: '2024', '2016-2017', '2000-е' или null",
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

Не выдумывай. Размеры могут говорить как '80 на 60', '80x60', 'восемьдесят на шестьдесят' — нормализуй в числа. Принято писать высота × ширина: первое число — height_cm, второе — width_cm."""


async def _to_mp3(audio_bytes: bytes) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-b:a", "64k", "-f", "mp3", "pipe:1",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(audio_bytes)
    if proc.returncode != 0 or not out:
        raise RuntimeError(f"ffmpeg: {err.decode(errors='ignore')[:200]}")
    return out


async def parse_voice(audio_bytes: bytes, audio_format: str = "ogg") -> dict:
    """Один вызов: распознаёт + парсит → JSON."""
    if not settings.ai_api_key:
        return {}

    if audio_format not in ("mp3", "wav"):
        audio_bytes, audio_format = await _to_mp3(audio_bytes), "mp3"
    audio_b64 = base64.b64encode(audio_bytes).decode()
    raw = await llm.chat({
        "model": settings.voice_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": {"data": audio_b64, "format": audio_format}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        "max_tokens": 2000,
        "reasoning_effort": "none",
    }, timeout=120.0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"transcript": raw}
