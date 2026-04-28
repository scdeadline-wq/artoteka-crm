from io import BytesIO

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from bot.handlers.auth import require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.handlers.keyboard import BTN_FIND
from bot.services.crm import crm

ASK_QUERY = 0

STATUS_FILTERS = {"available", "for_sale", "sold", "reserved", "draft", "review", "collection"}


async def _do_search(update: Update, query: str) -> None:
    artworks = await crm.search_artworks()
    q = query.strip().lower()

    if not q:
        await update.message.reply_text(
            f"В базе {len(artworks)} работ. Уточни запрос: номер, название, художник или статус."
        )
        return

    if q in STATUS_FILTERS:
        filtered = [a for a in artworks if (a.get("status") or "").lower() == q]
    elif q.isdigit():
        filtered = [a for a in artworks if str(a.get("inventory_number")) == q]
    else:
        filtered = [
            a for a in artworks
            if q in (a.get("title") or "").lower()
            or q in ((a.get("artist") or {}).get("name_ru") or "").lower()
            or q in ((a.get("artist") or {}).get("name_en") or "").lower()
        ]

    if not filtered:
        await update.message.reply_text("Ничего не нашёл")
        return

    if len(filtered) > 5:
        await update.message.reply_text(f"Нашёл {len(filtered)} работ — показываю первые 5:")
        filtered = filtered[:5]

    for artwork in filtered:
        full = await crm.get_artwork(artwork["id"])
        caption = format_artwork_card(full)
        images = sorted(full.get("images") or [], key=lambda i: (not i.get("is_primary"), i.get("sort_order", 0)))

        photo_blobs: list[bytes] = []
        for img in images[:10]:
            url = img.get("url")
            if not url:
                continue
            try:
                photo_blobs.append(await crm.download_image(url))
            except Exception:
                continue

        try:
            if len(photo_blobs) >= 2:
                media = [InputMediaPhoto(media=BytesIO(photo_blobs[0]), caption=caption, parse_mode="HTML")]
                media += [InputMediaPhoto(media=BytesIO(b)) for b in photo_blobs[1:]]
                await update.message.reply_media_group(media=media)
                continue
            if len(photo_blobs) == 1:
                await update.message.reply_photo(photo=BytesIO(photo_blobs[0]), caption=caption, parse_mode="HTML")
                continue
        except Exception:
            pass
        await update.message.reply_text(caption, parse_mode="HTML")


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
