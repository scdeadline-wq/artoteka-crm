"""Форматирование ответов бота и общий рендер результатов поиска."""
import asyncio
import logging
from io import BytesIO
from html import escape

from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message
from telegram.error import TimedOut

from bot.services.crm import crm

logger = logging.getLogger(__name__)


def _shrink(blob: bytes, max_side: int = 1280) -> bytes:
    """Ужимает фото до max_side по большей стороне перед отправкой в Telegram.

    В MinIO лежат оригиналы на несколько мегабайт — их загрузка в Telegram
    не успевала в write_timeout, бот получал TimedOut на уже доставленном
    сообщении и слал карточку второй раз текстом. Telegram всё равно жмёт
    фото примерно до 1280px, так что качество не теряем.
    """
    try:
        img = Image.open(BytesIO(blob))
        if max(img.size) <= max_side:
            return blob
        img.thumbnail((max_side, max_side))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception:
        return blob

STATUS_LABEL = {
    "draft": "Черновик",
    "review": "На проверке",
    "for_sale": "В продаже",
    "reserved": "Зарезервирована",
    "sold": "Продана",
    "collection": "В коллекции",
    "on_exhibition": "На выставке",
}


def status_button_keyboard(artwork_id: int) -> InlineKeyboardMarkup:
    """Кнопка «Изменить статус» под карточкой работы (обрабатывается в find.py)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Изменить статус", callback_data=f"chst:{artwork_id}"),
    ]])


CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "RUB": "₽", "GBP": "£", "CNY": "¥"}


def currency_symbol(code) -> str:
    if not code:
        return "$"
    return CURRENCY_SYMBOLS.get(str(code).upper(), str(code))


def _fmt_price(value, currency=None) -> str:
    if value in (None, ""):
        return "—"
    try:
        amount = f"{int(float(value)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"
    return f"{amount} {currency_symbol(currency)}"


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
    cur = a.get("currency")
    sale_price = _fmt_price(a.get("sale_price"), cur)
    status = (a.get("status") or "draft").lower()
    room = a.get("room") or {}
    room_name = room.get("name") if isinstance(room, dict) else None
    style = a.get("style_period")

    def _opt_name(v):
        return v.get("name") if isinstance(v, dict) else None
    warehouse_name = _opt_name(a.get("warehouse"))
    rack_name = _opt_name(a.get("rack"))
    shelf_name = _opt_name(a.get("shelf"))
    tags = a.get("tags") or []

    lines = [
        f"<b>{escape(artist_name)}</b> — {escape(str(title))}",
        f"Год: {year}",
        f"Техника: {escape(techs)}",
    ]
    if style:
        lines.append(f"Стиль: {escape(str(style))}")
    lines += [
        f"Размер: {size}",
        f"Цена: {sale_price}",
    ]
    if is_admin and a.get("purchase_price") not in (None, ""):
        lines.append(f"Закупка: {_fmt_price(a.get('purchase_price'), cur)}")
    storage_bits = []
    if room_name:
        storage_bits.append(f"Комната: {escape(str(room_name))}")
    if warehouse_name:
        storage_bits.append(f"Склад: {escape(str(warehouse_name))}")
    if rack_name:
        storage_bits.append(f"Стеллаж: {escape(str(rack_name))}")
    if shelf_name:
        storage_bits.append(f"Полка: {escape(str(shelf_name))}")
    lines.append(f"№ {inv}" + (" · " + " · ".join(storage_bits) if storage_bits else ""))
    if tags:
        lines.append("Теги: " + " ".join(f"#{escape(str(t))}" for t in tags))
    lines.append(f"Статус: {STATUS_LABEL.get(status, status)}")
    return "\n".join(lines)


async def send_artwork_results(
    message: Message,
    artworks: list[dict],
    *,
    is_admin: bool,
    limit: int = 5,
) -> None:
    """Печатает в чат до `limit` карточек с фото. Без результатов — пишет «Ничего не нашёл»."""
    if not artworks:
        await message.reply_text("Ничего не нашёл")
        return
    if len(artworks) > limit:
        await message.reply_text(f"Нашёл {len(artworks)} работ — показываю первые {limit}:")
        artworks = artworks[:limit]
    for artwork in artworks:
        full = await crm.get_artwork(artwork["id"])
        caption = format_artwork_card(full, is_admin=is_admin)
        images = sorted(
            full.get("images") or [],
            key=lambda i: (not i.get("is_primary"), i.get("sort_order", 0)),
        )
        photo_blobs: list[bytes] = []
        for img in images[:10]:
            url = img.get("url")
            if not url:
                continue
            try:
                blob = await crm.download_image(url)
                photo_blobs.append(await asyncio.to_thread(_shrink, blob))
            except Exception:
                continue
        markup = status_button_keyboard(full["id"])
        try:
            if len(photo_blobs) >= 2:
                # У media group нет inline-кнопок — шлём альбом, а кнопку отдельным сообщением.
                media = [InputMediaPhoto(media=BytesIO(photo_blobs[0]), caption=caption, parse_mode="HTML")]
                media += [InputMediaPhoto(media=BytesIO(b)) for b in photo_blobs[1:]]
                await message.reply_media_group(media=media)
                await message.reply_text(f"№ {full.get('inventory_number')} — действия:", reply_markup=markup)
                continue
            if len(photo_blobs) == 1:
                await message.reply_photo(
                    photo=BytesIO(photo_blobs[0]), caption=caption, parse_mode="HTML", reply_markup=markup,
                )
                continue
        except TimedOut:
            # Telegram при таймауте чаще всего УЖЕ доставил сообщение —
            # повторная отправка текстом давала дубль карточки. Не дублируем.
            logger.warning("TimedOut при отправке фото работы %s — фоллбек пропущен", full.get("id"))
            continue
        except Exception:
            logger.warning("Не удалось отправить фото работы %s — шлю текстом", full.get("id"), exc_info=True)
        await message.reply_text(caption, parse_mode="HTML", reply_markup=markup)
