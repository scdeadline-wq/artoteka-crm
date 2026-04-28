from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.auth import require_whitelist
from bot.handlers.keyboard import main_keyboard


HELP = """Привет! Я бот ArtSpace CRM.

Кнопки внизу или команды:
/add — добавить новую работу (фото + описание)
/find <запрос> — найти работу (по номеру, названию, художнику)
/sold <номер> — отметить работу как проданную
/client — добавить клиента/коллекционера
/help — эта справка"""


@require_whitelist
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, reply_markup=main_keyboard())


@require_whitelist
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, reply_markup=main_keyboard())
