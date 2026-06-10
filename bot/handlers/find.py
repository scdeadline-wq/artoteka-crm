from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from bot.handlers.auth import is_admin, require_whitelist
from bot.handlers.formatters import STATUS_LABEL, send_artwork_results, status_button_keyboard
from bot.handlers.keyboard import BTN_FIND
from bot.services.crm import crm

ASK_QUERY = 0

# Точные значения enum ArtworkStatus на бэкенде (несуществующий статус роняет запрос)
STATUS_FILTERS = {"for_sale", "sold", "reserved", "draft", "review", "collection", "on_exhibition"}


async def _do_search(update: Update, query: str) -> None:
    admin = is_admin(update)
    q = query.strip()

    if not q:
        all_artworks = await crm.search_artworks(limit=200)
        await update.message.reply_text(
            f"В базе {len(all_artworks)} работ. Уточни запрос: номер, название, художник или статус."
        )
        return

    if q.lower() in STATUS_FILTERS:
        filtered = await crm.search_artworks(status=q.lower(), limit=200)
    else:
        filtered = await crm.search_artworks(query=q, limit=200)

    await send_artwork_results(update.message, filtered, is_admin=admin)


@require_whitelist
async def find_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    query = " ".join(args).strip()
    if query:
        await _do_search(update, query)
        return ConversationHandler.END
    await update.message.reply_text("Что искать? (номер, название, художник или статус)")
    return ASK_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_search(update, update.message.text or "")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена")
    return ConversationHandler.END


# --- Смена статуса из карточки работы (inline-кнопка «Изменить статус») ---

# Значения совпадают с enum ArtworkStatus на бэкенде
STATUS_CHOICES = ["draft", "review", "for_sale", "reserved", "sold", "collection", "on_exhibition"]


def _statuses_keyboard(artwork_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for s in STATUS_CHOICES:
        row.append(InlineKeyboardButton(STATUS_LABEL.get(s, s), callback_data=f"setst:{artwork_id}:{s}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✖️ Отмена", callback_data=f"setst:{artwork_id}:cancel")])
    return InlineKeyboardMarkup(rows)


@require_whitelist
async def change_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «Изменить статус» на карточке → показываем варианты статусов."""
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) != 2:
        return
    try:
        artwork_id = int(parts[1])
    except ValueError:
        return
    await query.edit_message_reply_markup(reply_markup=_statuses_keyboard(artwork_id))


@require_whitelist
async def set_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбран новый статус → PATCH /artworks/{id}/status/?status=... (query-param!)."""
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) != 3:
        return
    artwork_id_str, status = parts[1], parts[2]
    try:
        artwork_id = int(artwork_id_str)
    except ValueError:
        return

    if status == "cancel":
        await query.edit_message_reply_markup(reply_markup=status_button_keyboard(artwork_id))
        return

    try:
        await crm.update_artwork_status(artwork_id, status)
    except Exception as e:
        await query.message.reply_text(f"Не удалось изменить статус: {e}")
        return
    await query.edit_message_reply_markup(reply_markup=status_button_keyboard(artwork_id))
    await query.message.reply_text(f"✅ Статус изменён: {STATUS_LABEL.get(status, status)}")


def build_status_handlers() -> list:
    return [
        CallbackQueryHandler(change_status_callback, pattern=r"^chst:"),
        CallbackQueryHandler(set_status_callback, pattern=r"^setst:"),
    ]


def build_find_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("find", find_start),
            MessageHandler(filters.Regex(rf"^{BTN_FIND}$"), find_start),
        ],
        states={
            ASK_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
