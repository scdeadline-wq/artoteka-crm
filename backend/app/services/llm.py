"""Единая точка вызова LLM — MixRoute (OpenAI-совместимый API).

OpenRouter больше не используем: аккаунт забанен. Провайдер, ключ, прокси и
модели — в .env (AI_BASE_URL, MIXROUTE_API_KEY, AI_PROXY, LLM_*_MODEL).
Имена моделей — как в каталоге MixRoute, без префиксов вида «google/».
"""
import base64
import logging
import re

import httpx

from app.config import settings

log = logging.getLogger(__name__)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)
_MD_IMAGE = re.compile(r"data:image/[a-z+]+;base64,([A-Za-z0-9+/=]+)")


class LLMError(Exception):
    pass


def configured() -> bool:
    return bool(settings.ai_api_key)


async def chat(body: dict, timeout: float = 120.0) -> dict:
    """POST /chat/completions. Возвращает JSON ответа или бросает LLMError с текстом провайдера."""
    if not settings.ai_api_key:
        raise LLMError("MIXROUTE_API_KEY не задан")
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
    async with httpx.AsyncClient(timeout=timeout, proxy=settings.ai_proxy or None) as client:
        r = await client.post(url, headers=headers, json=body)
        # reasoning_effort принимают не все модели — необязательный, снимаем и повторяем
        if r.status_code == 400 and "reasoning_effort" in body and "reasoning" in r.text:
            body = {k: v for k, v in body.items() if k != "reasoning_effort"}
            r = await client.post(url, headers=headers, json=body)
    if r.status_code != 200:
        log.error("LLM %s %s: %s", body.get("model"), r.status_code, r.text[:500])
        raise LLMError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


def text_of(data: dict) -> str:
    """content первого ответа без ```json-обёртки."""
    content = (data["choices"][0]["message"].get("content") or "").strip()
    m = _FENCE.match(content)
    return m.group(1) if m else content


def image_of(data: dict) -> bytes:
    """Картинка из ответа: поле images, части content или data-URL в markdown-тексте."""
    msg = data["choices"][0]["message"]
    parts = list(msg.get("images") or [])
    content = msg.get("content")
    if isinstance(content, list):
        parts += content
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "image_url":
            url = part["image_url"]["url"]
            if url.startswith("data:"):
                return base64.b64decode(url.split(",", 1)[1])
    if isinstance(content, str):
        m = _MD_IMAGE.search(content)
        if m:
            return base64.b64decode(m.group(1))
    raise LLMError(f"Модель не вернула изображение. Ключи ответа: {list(msg.keys())}")
