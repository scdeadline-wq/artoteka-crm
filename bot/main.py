"""ArtSpace Telegram Bot — точка входа.

Тонкий клиент к ArtSpace CRM API. Все данные хранятся в общей БД CRM,
бот только проксирует команды через HTTP.
"""
import logging

from telegram import BotCommand
from telegram.ext import Application, CommandHandler

from bot.config import settings
from bot.handlers.add import build_add_handler
from bot.handlers.client import build_client_handler
from bot.handlers.find import build_find_handler
from bot.handlers.sold import build_sold_handler
from bot.handlers.start import help_cmd, start
from bot.services.crm import crm

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("artspace-bot")


COMMANDS = [
    BotCommand("add", "Добавить работу"),
    BotCommand("find", "Найти работу"),
    BotCommand("sold", "Отметить продажу"),
    BotCommand("client", "Добавить клиента"),
    BotCommand("help", "Справка"),
]


async def _post_init(app: Application) -> None:
    await app.bot.set_my_commands(COMMANDS)


async def _on_shutdown(app: Application) -> None:
    await crm.close()


def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в окружении")
    if not settings.crm_user_email or not settings.crm_user_password:
        raise RuntimeError("CRM_USER_EMAIL/CRM_USER_PASSWORD не заданы")

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .post_shutdown(_on_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(build_add_handler())
    app.add_handler(build_find_handler())
    app.add_handler(build_sold_handler())
    app.add_handler(build_client_handler())

    logger.info("Bot запущен. Whitelist: %s", settings.allowed_ids)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
