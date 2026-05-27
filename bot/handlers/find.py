from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from bot.handlers.auth import is_admin, require_whitelist
from bot.handlers.formatters import send_artwork_results
from bot.handlers.keyboard import BTN_FIND
from bot.services.crm import crm

ASK_QUERY = 0

STATUS_FILTERS = {"available", "for_sale", "sold", "reserved", "draft", "review", "collection"}


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
