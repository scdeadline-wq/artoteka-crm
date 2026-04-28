"""Главная reply-клавиатура бота."""
from telegram import ReplyKeyboardMarkup, KeyboardButton

BTN_ADD = "➕ Добавить"
BTN_FIND = "🔍 Найти"
BTN_CLIENT = "👥 Клиент"
BTN_SOLD = "💰 Продажа"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_ADD), KeyboardButton(BTN_FIND)],
         [KeyboardButton(BTN_CLIENT), KeyboardButton(BTN_SOLD)]],
        resize_keyboard=True,
        is_persistent=True,
    )
