"""Команда /search — структурированный поиск по меню кнопок.

Категории:
- тег / тема (свободный текст)
- техника (выбор из справочника)
- цена (от / до)
- в раме
- свободные (status=for_sale)
"""
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.auth import is_admin, require_whitelist
from bot.handlers.formatters import send_artwork_results
from bot.services.crm import crm

MENU, AWAIT_VALUE = range(2)


def _menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏷 Тег", callback_data="s:tag"),
            InlineKeyboardButton("🖌 Техника", callback_data="s:technique"),
        ],
        [
            InlineKeyboardButton("💰 Цена", callback_data="s:price"),
            InlineKeyboardButton("🖼 В раме", callback_data="s:framed"),
        ],
        [InlineKeyboardButton("✅ Свободные", callback_data="s:available")],
        [InlineKeyboardButton("❌ Отмена", callback_data="s:cancel")],
    ])


def _techniques_keyboard(techniques: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for t in techniques:
        name = (t.get("name") or "?")[:25]
        row.append(InlineKeyboardButton(name, callback_data=f"st:{t['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="s:cancel")])
    return InlineKeyboardMarkup(rows)


def _parse_price_range(text: str) -> tuple[float | None, float | None]:
    """Принимает «от 50000», «до 200000», «50000-200000», «100000»."""
    cleaned = text.lower().replace(" ", "").replace(",", ".")
    m_from = re.search(r"от(\d+(?:\.\d+)?)", cleaned)
    m_to = re.search(r"до(\d+(?:\.\d+)?)", cleaned)
    if m_from or m_to:
        return (
            float(m_from.group(1)) if m_from else None,
            float(m_to.group(1)) if m_to else None,
        )
    m = re.match(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$", cleaned)
    if m:
        return float(m.group(1)), float(m.group(2))
    if re.match(r"^\d+(?:\.\d+)?$", cleaned):
        return None, float(cleaned)
    return None, None


@require_whitelist
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Что ищем?", reply_markup=_menu_keyboard())
    return MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("s:"):
        return MENU
    kind = query.data.split(":", 1)[1]

    if kind == "cancel":
        await query.edit_message_text("Отменено.")
        return ConversationHandler.END

    if kind == "framed":
        await query.edit_message_reply_markup(reply_markup=None)
        results = await crm.search_artworks_advanced(is_framed=True, limit=50)
        await send_artwork_results(query.message, results, is_admin=is_admin(update))
        return ConversationHandler.END

    if kind == "available":
        await query.edit_message_reply_markup(reply_markup=None)
        results = await crm.search_artworks(status="for_sale", limit=50)
        await send_artwork_results(query.message, results, is_admin=is_admin(update))
        return ConversationHandler.END

    if kind == "tag":
        context.user_data["search_kind"] = "tag"
        await query.edit_message_text("Введи тег (например «пейзаж»):")
        return AWAIT_VALUE

    if kind == "technique":
        try:
            techniques = await crm.list_techniques()
        except Exception:
            techniques = []
        if not techniques:
            await query.edit_message_text("Справочник техник пуст.")
            return ConversationHandler.END
        await query.edit_message_text(
            "Выбери технику:",
            reply_markup=_techniques_keyboard(techniques),
        )
        return MENU

    if kind == "price":
        context.user_data["search_kind"] = "price"
        await query.edit_message_text(
            "Введи диапазон. Примеры:\n"
            "• «от 50000»\n"
            "• «до 200000»\n"
            "• «50000-200000»\n"
            "• «100000» — до 100000"
        )
        return AWAIT_VALUE

    return MENU


async def technique_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("st:"):
        return MENU
    try:
        tid = int(query.data.split(":", 1)[1])
    except ValueError:
        return MENU
    await query.edit_message_reply_markup(reply_markup=None)
    results = await crm.search_artworks_advanced(technique_id=tid, limit=50)
    await send_artwork_results(query.message, results, is_admin=is_admin(update))
    return ConversationHandler.END


async def receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kind = context.user_data.pop("search_kind", None)
    text = (update.message.text or "").strip()
    if not text or not kind:
        await update.message.reply_text("Отмена")
        return ConversationHandler.END

    if kind == "tag":
        results = await crm.search_artworks_advanced(tag=text.lstrip("#"), limit=50)
    elif kind == "price":
        price_from, price_to = _parse_price_range(text)
        if price_from is None and price_to is None:
            await update.message.reply_text("Не понял диапазон. Попробуй ещё раз через /search.")
            return ConversationHandler.END
        results = await crm.search_artworks_advanced(
            price_from=price_from,
            price_to=price_to,
            limit=50,
        )
    else:
        await update.message.reply_text("Отмена")
        return ConversationHandler.END

    await send_artwork_results(update.message, results, is_admin=is_admin(update))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена")
    return ConversationHandler.END


def build_search_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            MENU: [
                CallbackQueryHandler(technique_callback, pattern=r"^st:"),
                CallbackQueryHandler(menu_callback, pattern=r"^s:"),
            ],
            AWAIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
