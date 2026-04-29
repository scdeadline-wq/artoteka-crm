"""Форматирование ответов бота."""
from html import escape

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
        f"<b>{escape(str(title))}</b>\n"
        f"Автор: {escape(artist_name)}\n"
        f"Год: {year}\n"
        f"Техника: {escape(techs)}\n"
        f"Размер: {size}\n"
        f"Цена: {price_str}\n"
        f"№ {inv}\n"
        f"Статус: {STATUS_LABEL.get(status, status)}"
    )
