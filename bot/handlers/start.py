from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.auth import require_whitelist


HELP = """Привет! Я бот ArtSpace CRM.

Команды:
/add — добавить новую работу (фото + описание)
/find <запрос> — найти работу (по номеру, названию, художнику)
/sold <номер> — отметить работу как проданную
/client — добавить клиента/коллекционера
/help — эта справка"""


@require_whitelist
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)


@require_whitelist
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)
