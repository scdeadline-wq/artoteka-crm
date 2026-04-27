"""Форматирование ответов бота."""
from html import escape

STATUS_EMOJI = {
    "draft": "📝",
    "review": "🔍",
    "for_sale": "🟢",
    "available": "🟢",
    "reserved": "🟡",
    "sold": "🔴",
    "collection": "📚",
}

STATUS_LABEL = {
    "draft": "Черновик",
    "review": "На проверке",
    "for_sale": "В продаже",
    "available": "Свободна",
    "reserved": "Зарезервирована",
    "sold": "Продана",
    "collection": "В коллекции",
}


def format_artwork_card(a: dict) -> str:
    inv = a.get("inventory_number")
    title = a.get("title") or "(без названия)"
    artist = a.get("artist") or {}
    artist_name = artist.get("name_ru") or artist.get("name_en") or "—"
    year = a.get("year") or "—"
    techs = ", ".join(t.get("name", "") for t in (a.get("techniques") or [])) or "—"
    w = a.get("width_cm")
    h = a.get("height_cm")
    size = f"{w} × {h} см" if w and h else "—"
    price = a.get("sale_price")
    price_str = f"{int(float(price)):,} ₽".replace(",", " ") if price else "—"
    status = (a.get("status") or "draft").lower()

    return (
        f"🎨 <b>{escape(str(title))}</b>\n"
        f"👤 {escape(artist_name)}, {year}\n"
        f"🖌 {escape(techs)}\n"
        f"📐 {size}\n"
        f"💰 {price_str}\n"
        f"📋 № {inv}\n"
        f"{STATUS_EMOJI.get(status, '')} {STATUS_LABEL.get(status, status)}"
    )
