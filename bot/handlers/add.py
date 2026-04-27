"""Команда /add — добавить произведение через фото + голосовое описание.

Сценарий:
1. /add → ждём фото
2. Фото получено → ждём голосовое (или текст)
3. Голос → Whisper → транскрипт → Claude парсер → превью
4. Подтверждение → создаём artist (если нет) → artwork → загружаем фото
"""
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters

from bot.handlers.auth import require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.services.crm import crm
from bot.services.parser import parse_description
from bot.services.whisper import transcribe

WAIT_PHOTO, WAIT_VOICE, CONFIRM = range(3)


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

    context.user_data["add_state"] = {"image_bytes": image_bytes}

    await update.message.reply_text(
        "🎙 Получил фото. Теперь отправь голосовое описание:\n"
        "автор, название, год, техника, размер, цена, стиль.\n\n"
        "Или напиши текстом."
    )
    return WAIT_VOICE


async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice or update.message.audio
    file = await voice.get_file()
    buf = BytesIO()
    await file.download_to_memory(buf)
    audio_bytes = buf.getvalue()

    await update.message.reply_text("🔄 Транскрибирую...")
    text = await transcribe(audio_bytes)
    if not text:
        await update.message.reply_text(
            "Не получилось транскрибировать. Whisper-ключ не настроен или ошибка API.\n"
            "Напиши описание текстом или /cancel"
        )
        return WAIT_VOICE

    await update.message.reply_text(f"📝 Распознал:\n«{text}»")
    return await _process_text(update, context, text)


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _process_text(update, context, update.message.text.strip())


async def _process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    parsed = await parse_description(text)
    context.user_data["add_state"]["parsed"] = parsed
    context.user_data["add_state"]["raw_text"] = text

    msg = "📋 Превью:\n"
    msg += f"🎨 Название: {parsed.get('title') or '—'}\n"
    msg += f"👤 Художник: {parsed.get('artist_name') or '—'}\n"
    msg += f"📅 Год: {parsed.get('year') or '—'}\n"
    if parsed.get("technique"):
        msg += f"🖌 Техника: {parsed['technique']}\n"
    if parsed.get("style_period"):
        msg += f"🎭 Стиль: {parsed['style_period']}\n"
    if parsed.get("width_cm") and parsed.get("height_cm"):
        msg += f"📐 Размер: {parsed['width_cm']} × {parsed['height_cm']} см\n"
    if parsed.get("sale_price"):
        msg += f"💰 Цена: {int(float(parsed['sale_price'])):,} ₽\n".replace(",", " ")
    if parsed.get("edition"):
        msg += f"🔢 Тираж: {parsed['edition']}\n"
    if parsed.get("location"):
        msg += f"📍 Локация: {parsed['location']}\n"
    if parsed.get("description"):
        msg += f"📝 {parsed['description']}\n"

    msg += "\nВсё верно? Да / Нет"
    await update.message.reply_text(msg)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer not in {"да", "yes", "y", "ок", "ok", "+", "✅"}:
        await update.message.reply_text(
            "Окей. Пришли голосовое заново или /cancel."
        )
        return WAIT_VOICE

    state = context.user_data["add_state"]
    parsed = state.get("parsed", {})

    artist_id = await _resolve_artist(parsed.get("artist_name"))
    if not artist_id:
        await update.message.reply_text(
            "Не понял художника. Напиши имя одной строкой:"
        )
        state["awaiting_artist_name"] = True
        return CONFIRM

    if state.pop("awaiting_artist_name", False):
        artist_id = await _resolve_artist(update.message.text.strip(), force_create=True)

    technique_ids = await _match_techniques(parsed.get("technique"))

    payload = _build_artwork_payload(parsed, artist_id, technique_ids)
    artwork = await crm.create_artwork(payload)
    await crm.upload_artwork_image(artwork["id"], state["image_bytes"], primary=True)

    full = await crm.get_artwork(artwork["id"])
    await update.message.reply_text("✅ Добавлено!\n" + format_artwork_card(full), parse_mode="HTML")

    context.user_data.clear()
    return ConversationHandler.END


async def _resolve_artist(name: str | None, force_create: bool = False) -> int | None:
    if not name:
        return None
    if not force_create:
        artists = await crm.list_artists()
        match = next(
            (
                a for a in artists
                if name.lower() in (a.get("name_ru") or "").lower()
                or name.lower() in (a.get("name_en") or "").lower()
            ),
            None,
        )
        if match:
            return match["id"]
    new_artist = await crm.create_artist(name_ru=name)
    return new_artist["id"]


async def _match_techniques(technique_text: str | None) -> list[int]:
    if not technique_text:
        return []
    techniques = await crm.list_techniques()
    text = technique_text.lower()
    matched = []
    for t in techniques:
        name = (t.get("name") or "").lower()
        # Грубое совпадение: материал или техника попадает в текст
        words = [w.strip(" ,.") for w in name.split(",")]
        if any(w and w in text for w in words):
            matched.append(t["id"])
    return matched


def _build_artwork_payload(parsed: dict, artist_id: int, technique_ids: list[int]) -> dict:
    payload = {
        "title": parsed.get("title"),
        "artist_id": artist_id,
        "year": int(parsed["year"]) if parsed.get("year") else None,
        "edition": parsed.get("edition"),
        "description": parsed.get("description") or parsed.get("notes"),
        "location": parsed.get("location"),
        "width_cm": float(parsed["width_cm"]) if parsed.get("width_cm") else None,
        "height_cm": float(parsed["height_cm"]) if parsed.get("height_cm") else None,
        "sale_price": float(parsed["sale_price"]) if parsed.get("sale_price") else None,
        "status": "draft",
        "technique_ids": technique_ids,
    }
    return {k: v for k, v in payload.items() if v is not None or k == "technique_ids"}


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена")
    context.user_data.clear()
    return ConversationHandler.END


def build_add_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            WAIT_VOICE: [
                MessageHandler(filters.VOICE | filters.AUDIO, receive_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text),
            ],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
