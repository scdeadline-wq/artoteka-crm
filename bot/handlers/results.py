"""Кнопки под результатами поиска: «Ещё», «Списком все», открыть карточку, PDF."""
import logging
from html import escape
from io import BytesIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.handlers.auth import is_admin, require_whitelist
from bot.handlers.formatters import (
    CARDS_PER_PAGE,
    LIST_PAGE_SIZE,
    STATUS_LABEL,
    _fmt_price,
    more_keyboard,
    send_artwork_cards,
    status_button_keyboard,
)
from bot.services.crm import crm

logger = logging.getLogger(__name__)

EXPIRED = "Результаты устарели — повтори поиск"


def _stored(context: ContextTypes.DEFAULT_TYPE, key: str) -> list[dict] | None:
    return (context.user_data.get("results") or {}).get(key)


def _parse(data: str | None, parts: int) -> list[str] | None:
    bits = (data or "").split(":")
    return bits if len(bits) == parts else None


@require_whitelist
async def more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """rmore:<key>:<offset> — следующие 5 карточек."""
    query = update.callback_query
    bits = _parse(query.data, 3)
    if not bits:
        await query.answer()
        return
    key, offset = bits[1], int(bits[2])
    rows = _stored(context, key)
    if rows is None:
        await query.answer(EXPIRED, show_alert=True)
        return
    await query.answer()
    # Убираем кнопки со старого сообщения, чтобы не нажали дважды
    await query.edit_message_reply_markup(reply_markup=None)
    chunk = rows[offset:offset + CARDS_PER_PAGE]
    await send_artwork_cards(query.message, chunk, is_admin=is_admin(update))
    shown = offset + len(chunk)
    await query.message.reply_text(
        f"Показаны 1–{shown} из {len(rows)}", reply_markup=more_keyboard(key, shown, len(rows))
    )


def _list_page(key: str, rows: list[dict], page: int) -> tuple[str, InlineKeyboardMarkup]:
    pages = max(1, -(-len(rows) // LIST_PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    chunk = rows[page * LIST_PAGE_SIZE:(page + 1) * LIST_PAGE_SIZE]
    lines = [f"<b>Работы {page * LIST_PAGE_SIZE + 1}–{page * LIST_PAGE_SIZE + len(chunk)} из {len(rows)}</b>", ""]
    for r in chunk:
        title = f"«{escape(r['title'])}»" if r.get("title") else "Без названия"
        year = f", {escape(str(r['year']))}" if r.get("year") else ""
        price = _fmt_price(r.get("price"), r.get("currency"))
        tail = STATUS_LABEL.get(r.get("status"), r.get("status") or "")
        if price != "—":
            tail += f" · {price}"
        lines.append(f"№ {r['inv']} — {escape(r.get('artist') or '—')}, {title}{year} · {tail}")
    lines += ["", "Нажми номер, чтобы открыть карточку."]

    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for r in chunk:
        row.append(InlineKeyboardButton(f"№ {r['inv']}", callback_data=f"rcard:{r['id']}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"rlist:{key}:{page - 1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("Дальше ▶️", callback_data=f"rlist:{key}:{page + 1}"))
    if nav:
        buttons.append(nav)
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


@require_whitelist
async def list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """rlist:<key>:<page> — компактный список всех найденных, по 20 на страницу."""
    query = update.callback_query
    bits = _parse(query.data, 3)
    if not bits:
        await query.answer()
        return
    key, page = bits[1], int(bits[2])
    rows = _stored(context, key)
    if rows is None:
        await query.answer(EXPIRED, show_alert=True)
        return
    await query.answer()
    text, markup = _list_page(key, rows, page)
    # Первая страница — новым сообщением, листание — правкой того же
    if page == 0 and not (query.message.text or "").startswith("Работы "):
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


@require_whitelist
async def card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """rcard:<id> — открыть карточку работы из списка."""
    query = update.callback_query
    await query.answer()
    bits = _parse(query.data, 2)
    if not bits:
        return
    await send_artwork_cards(query.message, [{"id": int(bits[1])}], is_admin=is_admin(update))


def _pdf_choice_keyboard(artwork_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 С ценой", callback_data=f"pdfg:{artwork_id}:1"),
            InlineKeyboardButton("📄 Без цены", callback_data=f"pdfg:{artwork_id}:0"),
        ],
        [InlineKeyboardButton("✖️ Отмена", callback_data=f"pdfx:{artwork_id}")],
    ])


@require_whitelist
async def pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """pdf:<id> — спросить, показывать ли цену в PDF."""
    query = update.callback_query
    await query.answer()
    bits = _parse(query.data, 2)
    if bits:
        await query.edit_message_reply_markup(reply_markup=_pdf_choice_keyboard(int(bits[1])))


@require_whitelist
async def pdf_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bits = _parse(query.data, 2)
    if bits:
        await query.edit_message_reply_markup(reply_markup=status_button_keyboard(int(bits[1])))


@require_whitelist
async def pdf_generate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """pdfg:<id>:<1|0> — собрать PDF в CRM и прислать файлом."""
    query = update.callback_query
    bits = _parse(query.data, 3)
    if not bits:
        await query.answer()
        return
    artwork_id, with_price = int(bits[1]), bits[2] == "1"
    await query.answer("Готовлю PDF…")
    await query.edit_message_reply_markup(reply_markup=status_button_keyboard(artwork_id))
    try:
        artwork = await crm.get_artwork(artwork_id)
        pdf = await crm.get_artwork_pdf(artwork_id, include_sale_price=with_price)
    except Exception:
        logger.exception("Не удалось сформировать PDF для работы %s", artwork_id)
        await query.message.reply_text("Не удалось сформировать PDF, попробуй ещё раз")
        return
    inv = artwork.get("inventory_number") or artwork_id
    await query.message.reply_document(
        document=BytesIO(pdf),
        filename=f"artoteka_{inv}.pdf",
        caption=f"№ {inv} — PDF {'с ценой' if with_price else 'без цены'}",
    )


def build_results_handlers() -> list:
    return [
        CallbackQueryHandler(more_callback, pattern=r"^rmore:"),
        CallbackQueryHandler(list_callback, pattern=r"^rlist:"),
        CallbackQueryHandler(card_callback, pattern=r"^rcard:"),
        CallbackQueryHandler(pdf_callback, pattern=r"^pdf:"),
        CallbackQueryHandler(pdf_cancel_callback, pattern=r"^pdfx:"),
        CallbackQueryHandler(pdf_generate_callback, pattern=r"^pdfg:"),
    ]
