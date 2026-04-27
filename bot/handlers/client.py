"""Команда /client — добавить нового клиента/коллекционера."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters

from bot.handlers.auth import require_whitelist
from bot.services.crm import crm

NAME, PHONE, EMAIL, DESCRIPTION = range(4)


@require_whitelist
async def client_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_data"] = {}
    await update.message.reply_text("Добавляем нового клиента.\nИмя?")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_data"]["name"] = update.message.text.strip()
    await update.message.reply_text("Телефон? (или /skip)")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_data"]["phone"] = update.message.text.strip()
    await update.message.reply_text("Email? (или /skip)")
    return EMAIL


async def skip_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Email? (или /skip)")
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_data"]["email"] = update.message.text.strip()
    await update.message.reply_text("Заметки / интересы / город / бюджет — одной строкой? (или /skip)")
    return DESCRIPTION


async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заметки / интересы / город / бюджет — одной строкой? (или /skip)")
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_data"]["description"] = update.message.text.strip()
    return await save(update, context)


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await save(update, context)


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = {k: v for k, v in context.user_data["client_data"].items() if v}
    payload["client_type"] = "buyer"
    client = await crm.create_client(payload)

    summary = f"✅ Клиент добавлен: {client['name']}"
    if client.get("phone"):
        summary += f"\n📱 {client['phone']}"
    if client.get("email"):
        summary += f"\n📧 {client['email']}"
    if client.get("description"):
        summary += f"\n📝 {client['description']}"
    await update.message.reply_text(summary)

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена")
    context.user_data.clear()
    return ConversationHandler.END


def build_client_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("client", client_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [
                CommandHandler("skip", skip_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
            EMAIL: [
                CommandHandler("skip", skip_email),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_email),
            ],
            DESCRIPTION: [
                CommandHandler("skip", skip_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
