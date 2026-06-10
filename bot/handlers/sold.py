"""Команда /sold — отметить работу проданной + создать запись о продаже."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.auth import require_whitelist
from bot.handlers.auth import is_admin
from bot.handlers.formatters import format_artwork_card
from bot.handlers.keyboard import BTN_SOLD
from bot.services.crm import crm

ASK_INV, CHOOSE_BUYER, ENTER_PRICE = range(3)


async def _enter_sold_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, inv: str) -> int:
    inv = inv.lstrip("№#").strip()
    if not inv.isdigit():
        await update.message.reply_text("Номер должен быть цифрой. Попробуй ещё раз или /cancel.")
        return ASK_INV

    # Точный поиск по инвентарному номеру (бэкенд по q-цифре матчит inventory_number точно)
    found = await crm.search_artworks(query=inv, limit=5)
    artwork = next((a for a in found if str(a.get("inventory_number")) == inv), None)
    if not artwork:
        await update.message.reply_text(f"Работа № {inv} не найдена. Введи другой номер или /cancel.")
        return ASK_INV

    context.user_data["sold_artwork"] = artwork

    msg = format_artwork_card(artwork, is_admin=is_admin(update))
    msg += "\n\nКто покупатель? Введи имя — поищу в базе клиентов.\nИли /skip для дилера."
    await update.message.reply_text(msg, parse_mode="HTML")
    return CHOOSE_BUYER


@require_whitelist
async def sold_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if args:
        return await _enter_sold_flow(update, context, args[0])
    await update.message.reply_text("Номер работы?")
    return ASK_INV


async def receive_inv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _enter_sold_flow(update, context, update.message.text or "")


def _buyers_keyboard(clients: list[dict], query: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(c["name"][:50], callback_data=f"soldclient:{c['id']}")]
        for c in clients[:10]
    ]
    rows.append([InlineKeyboardButton(f"➕ Создать нового: «{query[:30]}»", callback_data="soldclient:new")])
    return InlineKeyboardMarkup(rows)


async def choose_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Имя покупателя текстом → поиск по базе → кнопки с найденными + «Создать нового»."""
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Введи имя покупателя или /skip для дилера.")
        return CHOOSE_BUYER

    context.user_data["buyer_query"] = text
    clients = await crm.list_clients(query=text)
    context.user_data["found_clients"] = clients

    if clients:
        await update.message.reply_text(
            f"Нашёл {len(clients)} в базе. Выбери или создай нового:",
            reply_markup=_buyers_keyboard(clients, text),
        )
    else:
        await update.message.reply_text(
            f"В базе никого не нашёл по «{text}».",
            reply_markup=_buyers_keyboard([], text),
        )
    return CHOOSE_BUYER


async def buyer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопки выбора покупателя: существующий клиент или создание нового."""
    query = update.callback_query
    await query.answer()
    kind = (query.data or "").split(":", 1)[1]

    if kind == "new":
        name = context.user_data.get("buyer_query")
        if not name:
            await query.message.reply_text("Не помню имя. Введи имя покупателя ещё раз.")
            return CHOOSE_BUYER
        client = await crm.create_client({"name": name, "client_type": "buyer"})
        context.user_data["sold_client_id"] = client["id"]
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Создан клиент: {client['name']} (id={client['id']})\n\nЦена продажи в рублях?"
        )
        return ENTER_PRICE

    try:
        client_id = int(kind)
    except ValueError:
        return CHOOSE_BUYER
    context.user_data["sold_client_id"] = client_id
    found = context.user_data.get("found_clients", [])
    client = next((c for c in found if c["id"] == client_id), None)
    name = client["name"] if client else f"id={client_id}"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Покупатель: {name}\n\nЦена продажи в рублях?")
    return ENTER_PRICE


async def skip_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дилер — создаём/находим спец. клиента 'Дилер (без имени покупателя)'."""
    clients = await crm.list_clients(query="дилер")
    dealer = next((c for c in clients if c["name"].lower().startswith("дилер")), None)
    if not dealer:
        dealer = await crm.create_client({"name": "Дилер (без имени)", "client_type": "dealer"})
    context.user_data["sold_client_id"] = dealer["id"]
    await update.message.reply_text(
        "Покупатель: Дилер\n\nЦена продажи в рублях?"
    )
    return ENTER_PRICE


async def enter_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(" ", "").replace("₽", "").strip()
    try:
        price = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Введи число (можно без копеек)")
        return ENTER_PRICE

    artwork = context.user_data["sold_artwork"]
    client_id = context.user_data["sold_client_id"]

    # create_sale на бэкенде сам переводит работу в статус sold
    await crm.create_sale({
        "artwork_id": artwork["id"],
        "client_id": client_id,
        "sold_price": price,
    })

    await update.message.reply_text(
        f"✅ Готово!\n"
        f"🎨 {artwork.get('title') or '(без названия)'} → ПРОДАНА\n"
        f"💰 {int(price):,} ₽".replace(",", " ")
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена")
    context.user_data.clear()
    return ConversationHandler.END


def build_sold_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("sold", sold_start),
            MessageHandler(filters.Regex(rf"^{BTN_SOLD}$"), sold_start),
        ],
        states={
            ASK_INV: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_inv)],
            CHOOSE_BUYER: [
                CommandHandler("skip", skip_buyer),
                CallbackQueryHandler(buyer_callback, pattern=r"^soldclient:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_buyer),
            ],
            ENTER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
