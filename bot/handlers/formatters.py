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


def _fmt_price(value) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{int(float(value)):,} ₽".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def format_artwork_card(a: dict, *, is_admin: bool = False) -> str:
    inv = a.get("inventory_number")
    title = a.get("title") or "(без названия)"
    artist = a.get("artist") or {}
    artist_name = artist.get("name_ru") or artist.get("name_en") or "—"
    year = a.get("year") or "—"
    techs = ", ".join(t.get("name", "") for t in (a.get("techniques") or [])) or "—"
    w = a.get("width_cm")
    h = a.get("height_cm")
    size = f"{w} × {h} см" if w and h else "—"
    is_framed = a.get("is_framed")
    if is_framed:
        size = f"{size} · в раме" if size != "—" else "В раме"
    elif is_framed is False and size != "—":
        size = f"{size} · без рамы"
    sale_price = _fmt_price(a.get("sale_price"))
    status = (a.get("status") or "draft").lower()
    room = a.get("room") or {}
    room_name = room.get("name") if isinstance(room, dict) else None
    tags = a.get("tags") or []

    lines = [
        f"<b>{escape(artist_name)}</b> — {escape(str(title))}",
        f"Год: {year}",
        f"Техника: {escape(techs)}",
        f"Размер: {size}",
        f"Цена: {sale_price}",
    ]
    if is_admin and a.get("purchase_price") not in (None, ""):
        lines.append(f"Закупка: {_fmt_price(a.get('purchase_price'))}")
    lines.append(f"№ {inv}" + (f" · Комната: {escape(str(room_name))}" if room_name else ""))
    if tags:
        lines.append("Теги: " + " ".join(f"#{escape(str(t))}" for t in tags))
    lines.append(f"Статус: {STATUS_LABEL.get(status, status)}")
    return "\n".join(lines)
