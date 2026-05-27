"""Команды /delete и /trash. Только для admin."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot.handlers.auth import require_admin, require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.services.crm import crm


def _confirm_keyboard(artwork_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Да, удалить", callback_data=f"del:yes:{artwork_id}"),
        InlineKeyboardButton("Отмена", callback_data=f"del:no:{artwork_id}"),
    ]])


@require_whitelist
@require_admin
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text("Использование: /delete <номер инвентарный>")
        return
    inv_raw = args[0].lstrip("№#").strip()
    if not inv_raw.isdigit():
        await update.message.reply_text("Номер должен быть числом, например /delete 47")
        return
    inv = int(inv_raw)

    found = await crm.search_artworks(query=str(inv), limit=5)
    artwork = next((a for a in found if a.get("inventory_number") == inv), None)
    if not artwork:
        await update.message.reply_text(f"Работа № {inv} не найдена.")
        return

    full = await crm.get_artwork(artwork["id"])
    text = (
        "Удалить эту работу? Это можно отменить через /trash.\n\n"
        + format_artwork_card(full, is_admin=True)
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=_confirm_keyboard(artwork["id"]),
    )


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) != 3 or parts[0] != "del":
        return
    action, artwork_id_str = parts[1], parts[2]
    try:
        artwork_id = int(artwork_id_str)
    except ValueError:
        return

    if action == "no":
        await query.edit_message_text("Отменено.")
        return
    if action != "yes":
        return

    try:
        await crm.soft_delete_artwork(artwork_id)
    except Exception as e:
        await query.edit_message_text(f"Не удалось удалить: {e}")
        return
    await query.edit_message_text(
        f"🗑 Работа удалена. Восстановить — /trash (id {artwork_id})."
    )


def _restore_keyboard(artwork_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("♻️ Восстановить", callback_data=f"restore:{artwork_id}"),
    ]])


@require_whitelist
@require_admin
async def trash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = await crm.list_trash(limit=50)
    if not items:
        await update.message.reply_text("Корзина пуста.")
        return

    await update.message.reply_text(f"В корзине {len(items)} работ:")
    for a in items[:20]:
        artist = a.get("artist") or {}
        artist_name = artist.get("name_ru") or artist.get("name_en") or "—"
        title = a.get("title") or "(без названия)"
        inv = a.get("inventory_number")
        deleted = (a.get("deleted_at") or "")[:10]
        text = f"<b>{artist_name} — {title}</b>\n№ {inv} · удалена {deleted}"
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=_restore_keyboard(a["id"]),
        )
    if len(items) > 20:
        await update.message.reply_text(f"...и ещё {len(items) - 20}. Чтобы увидеть остальное, чисти первые.")


async def restore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) != 2 or parts[0] != "restore":
        return
    try:
        artwork_id = int(parts[1])
    except ValueError:
        return
    try:
        await crm.restore_artwork(artwork_id)
    except Exception as e:
        await query.edit_message_text(f"Не удалось восстановить: {e}")
        return
    await query.edit_message_text(f"♻️ Работа восстановлена (id {artwork_id}).")


def build_delete_handlers() -> list:
    return [
        CommandHandler("delete", delete_cmd),
        CommandHandler("trash", trash_cmd),
        CallbackQueryHandler(delete_callback, pattern=r"^del:"),
        CallbackQueryHandler(restore_callback, pattern=r"^restore:"),
    ]
