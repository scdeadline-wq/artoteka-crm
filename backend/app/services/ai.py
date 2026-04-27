"""AI-анализ фото произведений искусства через OpenRouter."""
import base64
import json
import httpx

from app.config import settings
from app.services.web_search import search_artwork_by_image

SYSTEM_PROMPT = """Ты — ведущий искусствовед, куратор и оценщик с 30-летним стажем.
Тебе отправляют фотографию произведения искусства и (опционально) результаты реверс-поиска по этому изображению в Яндексе. Проанализируй и верни JSON:

{
  "title": "Реальное название работы. Если в результатах поиска есть совпадение с этим изображением (Wikipedia, artchive.ru, gallerix.ru, аукционные дома) — возьми название оттуда. Если визуально читается подпись — используй её. НЕ ВЫДУМЫВАЙ. Если не уверен — null.",
  "artist_name": "Имя художника (Фамилия Имя) на русском. Из результатов поиска или подписи на работе. НЕ предполагай и не пиши '(предположительно)'. Если не уверен — null.",
  "year_estimate": "Год или десятилетие (напр. '1967' или '1960-е'). Определи по стилистике, материалам, манере.",
  "techniques": ["Выбери из списка: Холст, масло | Картон, масло | Дерево, масло | Холст, темпера | Холст, акрил | Холст, смешанная техника | Бумага, графитный карандаш | Бумага, тушь | Бумага, тушь, перо | Бумага, акварель | Бумага, гуашь | Бумага, пастель | Бумага, сангина | Бумага, соус | Бумага, уголь | Бумага, цветные карандаши | Бумага, смешанная техника | Литография | Офорт | Ксилография | Линогравюра | Шелкография (сериграфия) | Бронза | Керамика | Фарфор | Дерево | Гипс | Фарфор, роспись | Стекло | Эмаль | Текстиль | Фотография, серебряно-желатиновая печать | Фотография, цифровая печать | Смешанная техника | Коллаж | Инсталляция"],
  "description": "Развёрнутое, живое описание для каталога (3-5 предложений). Опиши сюжет, композицию, колорит, настроение. Пиши как для покупателя-коллекционера — увлекательно, со знанием контекста. Упомяни художественные приёмы.",
  "condition": "Видимое состояние: отличное / хорошее / удовлетворительное / есть повреждения. Если видны дефекты — опиши кратко.",
  "style_period": "Художественный стиль и направление (напр. 'соц-арт', 'московский концептуализм', 'наивное искусство', 'соцреализм', 'авангард', 'импрессионизм', 'поп-арт'). Можно несколько через запятую.",
  "tags": ["5-10 тегов для поиска и рекомендаций: тематика, мотивы, настроение, эпоха. Напр.: 'советское', 'ирония', 'политическое', 'фигуративное', 'застолье', 'анималистика'"],
  "width_cm": "Оценка ширины произведения в сантиметрах (только число). Определи по технике, жанру, пропорциям. Станковая живопись обычно 40-120 см, графика 20-60 см, миниатюры 10-20 см. null если невозможно.",
  "height_cm": "Оценка высоты произведения в сантиметрах (только число). Учитывай пропорции изображения.",
  "estimated_price_rub": "Оценка рыночной стоимости в рублях. Учитывай художника, период, технику, размер, состояние. Число без пробелов или null.",
  "confidence": "low / medium / high"
}

Отвечай ТОЛЬКО валидным JSON. Не оборачивай в markdown. Если не можешь определить поле — ставь null."""


async def analyze_artwork_image(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Отправляет фото в AI и возвращает предзаполненные поля.

    Перед вызовом Gemini делает реверс-поиск через Яндекс и передаёт
    найденные совпадения в промпт как контекст для атрибуции.
    """
    from app.services.image_utils import normalize_image

    if not settings.openrouter_api_key:
        return {"error": "OpenRouter API key not configured"}

    # Реверс-поиск Яндекса делаем по ОРИГИНАЛЬНЫМ байтам — perceptual hash
    # чувствителен к перепаковке, после normalize_image Яндекс не находит совпадений
    search_results = await search_artwork_by_image(image_bytes)

    # Нормализуем формат (HEIC, WEBP → JPEG) для Gemini
    image_bytes = normalize_image(image_bytes)

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    user_text = _build_user_prompt(search_results)

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
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                            {"type": "text", "text": user_text},
                        ],
                    },
                ],
                "max_tokens": 1000,
            },
        )
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"OpenRouter {response.status_code}: {response.text[:500]}",
                request=response.request,
                response=response,
            )
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    # Парсим JSON из ответа (может быть обёрнут в ```json...```)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]

    parsed = json.loads(content)
    parsed["_sources"] = search_results
    return parsed


def _build_user_prompt(search_results: list[dict]) -> str:
    if not search_results:
        return "Проанализируй это произведение искусства. Реверс-поиск ничего не дал — опирайся только на визуальные признаки."

    lines = ["Проанализируй это произведение искусства.", "", "Результаты реверс-поиска Яндекса по этому изображению:"]
    for i, r in enumerate(search_results, 1):
        title = r.get("title") or "—"
        source = r.get("source") or "—"
        snippet = r.get("snippet") or ""
        lines.append(f"{i}. {title} ({source}) — {snippet}".strip())
    lines.append("")
    lines.append("Используй эти источники для определения title и artist_name, если совпадение явное.")
    return "\n".join(lines)
