from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.auth import require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.services.crm import crm

STATUS_FILTERS = {"available", "for_sale", "sold", "reserved", "draft", "review", "collection"}


@require_whitelist
async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    query = " ".join(args).strip().lower()

    artworks = await crm.search_artworks()

    if not query:
        await update.message.reply_text(
            f"В базе {len(artworks)} работ. Уточни запрос: /find <номер | название | художник | статус>"
        )
        return

    # Статусный фильтр
    if query in STATUS_FILTERS:
        filtered = [a for a in artworks if (a.get("status") or "").lower() == query]
    elif query.isdigit():
        # Поиск по inventory_number
        filtered = [a for a in artworks if str(a.get("inventory_number")) == query]
    else:
        filtered = [
            a for a in artworks
            if query in (a.get("title") or "").lower()
            or query in ((a.get("artist") or {}).get("name_ru") or "").lower()
            or query in ((a.get("artist") or {}).get("name_en") or "").lower()
        ]

    if not filtered:
        await update.message.reply_text("Ничего не нашёл")
        return

    if len(filtered) > 5:
        await update.message.reply_text(
            f"Нашёл {len(filtered)} работ — показываю первые 5:"
        )
        filtered = filtered[:5]

    for artwork in filtered:
        await update.message.reply_text(format_artwork_card(artwork), parse_mode="HTML")
