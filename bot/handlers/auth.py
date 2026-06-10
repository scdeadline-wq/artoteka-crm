"""Whitelist-проверка для всех handlers."""
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import settings


def is_admin(update: Update) -> bool:
    """Админ = из ADMIN_TELEGRAM_IDS. Видит закупку, может удалять."""
    user = update.effective_user
    return bool(user and user.id in settings.admin_ids)


def require_whitelist(handler):
    """Декоратор: пропускает handler только если telegram_id есть в ALLOWED_TELEGRAM_IDS."""
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id not in settings.allowed_ids:
            if update.message:
                await update.message.reply_text(
                    f"Нет доступа. Сообщи администратору свой Telegram ID: {user.id if user else '?'}"
                )
            elif update.callback_query:
                await update.callback_query.answer("Нет доступа", show_alert=True)
            return
        return await handler(update, context)

    return wrapper


def require_admin(handler):
    """Декоратор: пропускает handler только для admin-ов из ADMIN_TELEGRAM_IDS."""
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            if update.message:
                await update.message.reply_text("Эта команда доступна только администратору.")
            elif update.callback_query:
                await update.callback_query.answer("Только для администратора", show_alert=True)
            return
        return await handler(update, context)

    return wrapper
