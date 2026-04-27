"""Команда /add — добавить произведение через фото + текстовое описание."""
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters

from bot.handlers.auth import require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.services.crm import crm
from bot.services.parser import parse_description

WAIT_PHOTO, WAIT_DESCRIPTION, CONFIRM = range(3)


@require_whitelist
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_state"] = {}
    await update.message.reply_text("📸 Отправь фото произведения")
    return WAIT_PHOTO


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    buf = BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    await update.message.reply_text("🔍 AI анализирует фото...")

    try:
        ai_result = await crm.analyze_image(image_bytes)
    except Exception as e:
        await update.message.reply_text(f"Ошибка AI: {e}\nПопробуй ещё раз: /add")
        return ConversationHandler.END

    suggested = ai_result.get("suggested") or {}
    sources = ai_result.get("sources") or []

    context.user_data["add_state"] = {
        "image_bytes": image_bytes,
        "suggested": suggested,
        "sources": sources,
    }

    msg = "🤖 AI распознал:\n"
    if suggested.get("title"):
        msg += f"🎨 {suggested['title']}\n"
    if suggested.get("artist_name_suggestion"):
        msg += f"👤 {suggested['artist_name_suggestion']}\n"
    if suggested.get("year"):
        msg += f"📅 {suggested['year']}\n"
    if suggested.get("style_period"):
        msg += f"🎭 {suggested['style_period']}\n"
    if suggested.get("width_cm") and suggested.get("height_cm"):
        msg += f"📐 {suggested['width_cm']} × {suggested['height_cm']} см\n"
    if suggested.get("confidence"):
        msg += f"📊 Уверенность: {suggested['confidence']}\n"
    if sources:
        msg += f"\n🔗 Найдено {len(sources)} источников в интернете\n"

    msg += (
        "\nДополни голосом или текстом: автор, название, год, техника, размер, цена.\n"
        "Или /skip если AI всё распознал правильно."
    )
    await update.message.reply_text(msg)
    return WAIT_DESCRIPTION


async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parsed = await parse_description(text)
    context.user_data["add_state"]["parsed"] = parsed
    context.user_data["add_state"]["raw_description"] = text
    return await show_preview(update, context)


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_state"]["parsed"] = {}
    return await show_preview(update, context)


async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data["add_state"]
    suggested = state["suggested"]
    parsed = state.get("parsed", {})

    # Слияние: parsed (от пользователя) приоритетнее AI suggested
    merged = {
        "title": parsed.get("title") or suggested.get("title"),
        "artist_name": parsed.get("artist_name") or suggested.get("artist_name_suggestion"),
        "year": parsed.get("year") or suggested.get("year"),
        "width_cm": parsed.get("width_cm") or suggested.get("width_cm"),
        "height_cm": parsed.get("height_cm") or suggested.get("height_cm"),
        "sale_price": parsed.get("sale_price") or suggested.get("estimated_price_rub"),
        "edition": parsed.get("edition"),
        "location": parsed.get("location"),
        "description": suggested.get("description"),
        "condition": suggested.get("condition"),
        "technique_text": parsed.get("technique"),
        "ai_techniques": suggested.get("techniques") or [],
        "notes": parsed.get("notes"),
    }
    state["merged"] = merged

    msg = "📋 Превью:\n"
    msg += f"🎨 Название: {merged['title'] or '—'}\n"
    msg += f"👤 Художник: {merged['artist_name'] or '—'}\n"
    msg += f"📅 Год: {merged['year'] or '—'}\n"
    if merged["ai_techniques"]:
        msg += f"🖌 Техника: {', '.join(t['name'] for t in merged['ai_techniques'])}\n"
    if merged.get("technique_text"):
        msg += f"🖌 (из описания): {merged['technique_text']}\n"
    if merged["width_cm"] and merged["height_cm"]:
        msg += f"📐 Размер: {merged['width_cm']} × {merged['height_cm']} см\n"
    if merged["sale_price"]:
        msg += f"💰 Цена: {int(float(merged['sale_price'])):,} ₽\n".replace(",", " ")
    if merged.get("edition"):
        msg += f"🔢 Тираж: {merged['edition']}\n"
    if merged.get("location"):
        msg += f"📍 Локация: {merged['location']}\n"

    msg += "\nВсё верно? Да / Нет"
    await update.message.reply_text(msg)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer not in {"да", "yes", "y", "ок", "ok", "+", "✅"}:
        await update.message.reply_text(
            "Окей, /add заново когда нужно. (Inline-редактирование пока не сделано.)"
        )
        context.user_data.clear()
        return ConversationHandler.END

    state = context.user_data["add_state"]
    merged = state["merged"]

    # Найти/создать художника
    artist_id = None
    artist_name = merged.get("artist_name")
    if artist_name:
        artists = await crm.list_artists()
        match = next(
            (
                a for a in artists
                if artist_name.lower() in (a.get("name_ru") or "").lower()
                or artist_name.lower() in (a.get("name_en") or "").lower()
            ),
            None,
        )
        if match:
            artist_id = match["id"]
        else:
            new_artist = await crm.create_artist(name_ru=artist_name)
            artist_id = new_artist["id"]
            await update.message.reply_text(f"➕ Создан художник: {artist_name}")

    if not artist_id:
        await update.message.reply_text(
            "Не получилось определить художника. Назови его одним сообщением:"
        )
        # Сохраняем превью, ждём имя
        state["awaiting_artist"] = True
        return CONFIRM

    payload = {
        "title": merged["title"],
        "artist_id": artist_id,
        "year": int(merged["year"]) if merged.get("year") else None,
        "edition": merged.get("edition"),
        "description": merged.get("description"),
        "condition": merged.get("condition"),
        "location": merged.get("location"),
        "width_cm": float(merged["width_cm"]) if merged.get("width_cm") else None,
        "height_cm": float(merged["height_cm"]) if merged.get("height_cm") else None,
        "sale_price": float(merged["sale_price"]) if merged.get("sale_price") else None,
        "status": "draft",
        "technique_ids": [t["id"] for t in merged.get("ai_techniques", [])],
    }
    payload = {k: v for k, v in payload.items() if v is not None or k == "technique_ids"}

    artwork = await crm.create_artwork(payload)
    await crm.upload_artwork_image(artwork["id"], state["image_bytes"], primary=True)

    # Перечитываем чтобы получить полную карточку
    full = await crm.get_artwork(artwork["id"])
    await update.message.reply_text("✅ Добавлено!\n" + format_artwork_card(full), parse_mode="HTML")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена")
    context.user_data.clear()
    return ConversationHandler.END


def build_add_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            WAIT_DESCRIPTION: [
                CommandHandler("skip", skip_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
            ],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
