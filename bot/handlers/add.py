"""Команда /add — добавить произведение через фото + голосовое описание.

Сценарий:
1. /add → ждём фото
2. Фото получено → ждём голосовое (или текст)
3. Голос → Whisper → транскрипт → Claude парсер → превью
4. Подтверждение → создаём artist (если нет) → artwork → загружаем фото
"""
from io import BytesIO

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)

from bot.handlers.auth import require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.handlers.keyboard import BTN_ADD
from bot.services.crm import crm
from bot.services.parser import parse_description
from bot.services.voice_parser import parse_voice

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

    await update.message.reply_text("🔄 Распознаю и парсю...")
    try:
        parsed = await parse_voice(audio_bytes, audio_format="ogg")
    except Exception as e:
        await update.message.reply_text(
            f"Ошибка распознавания: {e}\nНапиши текстом или /cancel"
        )
        return WAIT_VOICE

    if not parsed:
        await update.message.reply_text(
            "Не получилось распознать. Напиши описание текстом или /cancel"
        )
        return WAIT_VOICE

    transcript = parsed.pop("transcript", "") if isinstance(parsed, dict) else ""
    if transcript:
        await update.message.reply_text(f"📝 Распознал:\n«{transcript}»")

    return await _show_preview(update, context, parsed)


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parsed = await parse_description(text)
    return await _show_preview(update, context, parsed)


EDITABLE_FIELDS = [
    ("title", "🎨 Название"),
    ("artist_name", "👤 Художник"),
    ("year", "📅 Год"),
    ("technique", "🖌 Техника"),
    ("size", "📐 Размер"),
    ("sale_price", "💰 Цена"),
]


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Сохранить", callback_data="add:confirm"),
            InlineKeyboardButton("✏️ Поправить", callback_data="add:edit"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="add:cancel")],
    ])


def _edit_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"edit:{key}")]
        for key, label in EDITABLE_FIELDS
    ]
    rows.append([InlineKeyboardButton("← Назад", callback_data="add:back")])
    return InlineKeyboardMarkup(rows)


def _format_preview(parsed: dict) -> str:
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
    return msg


async def _show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, parsed: dict):
    context.user_data["add_state"]["parsed"] = parsed
    await update.message.reply_text(_format_preview(parsed), reply_markup=_confirm_keyboard())
    return CONFIRM


async def _do_create(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Реально создаёт работу. Возвращает следующий state."""
    state = context.user_data["add_state"]
    parsed = state.get("parsed", {})

    artist_id = await _resolve_artist(parsed.get("artist_name"))
    if not artist_id:
        await context.bot.send_message(chat_id=chat_id, text="Не понял художника. Напиши имя одной строкой:")
        state["awaiting_artist_name"] = True
        return CONFIRM

    technique_ids = await _match_techniques(parsed.get("technique"))
    if parsed.get("technique") and not technique_ids:
        import logging
        logging.getLogger(__name__).warning(
            "Не сматчили технику для распознанного '%s' (parsed: %s)",
            parsed.get("technique"), parsed,
        )

    payload = _build_artwork_payload(parsed, artist_id, technique_ids)
    artwork = await crm.create_artwork(payload)
    await crm.upload_artwork_image(artwork["id"], state["image_bytes"], primary=True)

    full = await crm.get_artwork(artwork["id"])
    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Добавлено!\n" + format_artwork_card(full),
        parse_mode="HTML",
    )

    context.user_data.clear()
    return ConversationHandler.END


FIELD_PROMPTS = {
    "title": "Введи новое название (или «-» чтобы очистить):",
    "artist_name": "Введи имя художника:",
    "year": "Введи год (число):",
    "technique": "Введи технику (например, «Холст, масло»):",
    "size": "Введи размер: «ширина x высота» в см (например, 60x80):",
    "sale_price": "Введи цену в рублях (число):",
}


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline-кнопки на превью: Сохранить / Поправить / Отмена / Назад / выбор поля."""
    query = update.callback_query
    await query.answer()
    state = context.user_data.get("add_state", {})

    if query.data == "add:cancel":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ Отменено. Можешь начать заново через ➕ Добавить.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "add:edit":
        await query.edit_message_text(
            _format_preview(state.get("parsed", {})) + "\nЧто поправить?",
            reply_markup=_edit_keyboard(),
        )
        return CONFIRM

    if query.data == "add:back":
        await query.edit_message_text(
            _format_preview(state.get("parsed", {})),
            reply_markup=_confirm_keyboard(),
        )
        return CONFIRM

    if query.data.startswith("edit:"):
        field = query.data.split(":", 1)[1]
        state["editing_field"] = field
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(FIELD_PROMPTS.get(field, "Введи новое значение:"))
        return CONFIRM

    # add:confirm
    await query.edit_message_reply_markup(reply_markup=None)
    return await _do_create(query.message.chat_id, context)


def _apply_field(parsed: dict, field: str, value: str) -> str | None:
    """Записывает value в parsed для field. Возвращает текст ошибки или None."""
    value = value.strip()
    if field == "size":
        import re
        m = re.search(r"(\d+(?:[,.]\d+)?)\s*[xхХ×*]\s*(\d+(?:[,.]\d+)?)", value)
        if not m:
            return "Не понял размер. Формат: 60x80 или 60 x 80"
        parsed["width_cm"] = float(m.group(1).replace(",", "."))
        parsed["height_cm"] = float(m.group(2).replace(",", "."))
        return None
    if field == "year":
        digits = "".join(c for c in value if c.isdigit())
        if not digits:
            return "Год должен быть числом."
        parsed["year"] = int(digits[:4])
        return None
    if field == "sale_price":
        digits = "".join(c for c in value if c.isdigit())
        if not digits:
            return "Цена должна быть числом."
        parsed["sale_price"] = float(digits)
        return None
    # title, artist_name, technique — строки; «-» очищает
    parsed[field] = None if value == "-" else value
    return None


async def confirm_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Текст в state CONFIRM: либо ввод значения для редактируемого поля, либо Да/Нет."""
    state = context.user_data.get("add_state", {})
    text = (update.message.text or "").strip()

    # Редактирование выбранного поля
    field = state.pop("editing_field", None)
    if field:
        parsed = state.setdefault("parsed", {})
        err = _apply_field(parsed, field, text)
        if err:
            state["editing_field"] = field  # вернуть флаг
            await update.message.reply_text(err)
            return CONFIRM
        await update.message.reply_text(
            _format_preview(parsed),
            reply_markup=_confirm_keyboard(),
        )
        return CONFIRM

    # Дозапрос имени художника (когда AI не понял)
    if state.pop("awaiting_artist_name", False):
        state.setdefault("parsed", {})["artist_name"] = text
        return await _do_create(update.message.chat_id, context)

    # Текстовый Да/Нет fallback (если по какой-то причине не сработали кнопки)
    answer = text.lower()
    if answer in {"да", "yes", "y", "ок", "ok", "+", "✅"}:
        return await _do_create(update.message.chat_id, context)
    if answer in {"нет", "no", "n", "❌"}:
        await update.message.reply_text("❌ Отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    await update.message.reply_text("Нажми кнопку под превью или /cancel.")
    return CONFIRM


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
    text = technique_text.lower().strip()

    for t in techniques:
        if (t.get("name") or "").lower() == text:
            return [t["id"]]

    best_id: int | None = None
    best_score = 0
    for t in techniques:
        name = (t.get("name") or "").lower()
        words = [w.strip(" ,.") for w in name.split(",") if w.strip(" ,.")]
        if not words:
            continue
        if all(w in text for w in words) and len(words) > best_score:
            best_id = t["id"]
            best_score = len(words)
    return [best_id] if best_id else []


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
        entry_points=[
            CommandHandler("add", add_start),
            MessageHandler(filters.Regex(rf"^{BTN_ADD}$"), add_start),
        ],
        states={
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            WAIT_VOICE: [
                MessageHandler(filters.VOICE | filters.AUDIO, receive_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_callback, pattern=r"^(add:|edit:)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
