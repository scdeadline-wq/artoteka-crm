"""Транскрипция аудио через OpenAI Whisper."""
from __future__ import annotations

import httpx

from bot.config import settings

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    """Транскрибирует голосовое сообщение в текст. Возвращает '' при ошибке."""
    if not settings.openai_api_key:
        return ""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            WHISPER_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"file": (filename, audio_bytes, "audio/ogg")},
            data={"model": settings.whisper_model, "language": "ru"},
        )
        response.raise_for_status()
        return response.json().get("text", "")
