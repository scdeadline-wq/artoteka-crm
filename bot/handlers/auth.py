"""Whitelist-проверка для всех handlers."""
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import settings


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
            return
        return await handler(update, context)

    return wrapper
