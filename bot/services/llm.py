"""Вызов LLM из бота — MixRoute (OpenAI-совместимый), те же ключ и прокси, что у backend."""
from __future__ import annotations

import logging
import re

import httpx

from bot.config import settings

log = logging.getLogger(__name__)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


async def chat(body: dict, timeout: float = 60.0) -> str:
    """POST /chat/completions → content первого ответа без ```json-обёртки."""
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
        r.raise_for_status()
    content = (r.json()["choices"][0]["message"].get("content") or "").strip()
    m = _FENCE.match(content)
    return m.group(1) if m else content
