"""Команда /sold — отметить работу проданной + создать запись о продаже."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters

from bot.handlers.auth import require_whitelist
from bot.handlers.formatters import format_artwork_card
from bot.services.crm import crm

CHOOSE_BUYER, ENTER_NEW_CLIENT, ENTER_PRICE = range(3)


@require_whitelist
async def sold_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text("Использование: /sold <номер_работы>")
        return ConversationHandler.END

    inv = args[0].lstrip("№#")
    if not inv.isdigit():
        await update.message.reply_text("Номер должен быть цифрой")
        return ConversationHandler.END

    artworks = await crm.search_artworks()
    artwork = next((a for a in artworks if str(a.get("inventory_number")) == inv), None)
    if not artwork:
        await update.message.reply_text(f"Работа № {inv} не найдена")
        return ConversationHandler.END

    context.user_data["sold_artwork"] = artwork
    clients = await crm.list_clients()
    context.user_data["clients"] = clients

    msg = format_artwork_card(artwork) + "\n\nКто покупатель?"
    if clients:
        msg += "\n\nСуществующие клиенты:"
        for c in clients[:10]:
            msg += f"\n  {c['id']} — {c['name']}"
        msg += "\n\nВведи ID клиента, или новое имя, или /skip для дилера."
    else:
        msg += "\n\nВведи имя нового клиента (или /skip для дилера)."

    await update.message.reply_text(msg, parse_mode="HTML")
    return CHOOSE_BUYER


async def choose_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    clients = context.user_data.get("clients", [])

    # Цифра — ID существующего клиента
    if text.isdigit():
        client_id = int(text)
        client = next((c for c in clients if c["id"] == client_id), None)
        if client:
            context.user_data["sold_client_id"] = client_id
            await update.message.reply_text(
                f"Покупатель: {client['name']}\n\nЦена продажи в рублях?"
            )
            return ENTER_PRICE
        await update.message.reply_text(f"Клиент с id={client_id} не найден. Введи имя нового или /skip.")
        return CHOOSE_BUYER

    # Новый клиент по имени
    new_client = await crm.create_client({"name": text, "client_type": "buyer"})
    context.user_data["sold_client_id"] = new_client["id"]
    await update.message.reply_text(
        f"Создан клиент: {new_client['name']} (id={new_client['id']})\n\nЦена продажи в рублях?"
    )
    return ENTER_PRICE


async def skip_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дилер — создаём/находим спец. клиента 'Дилер (без имени покупателя)'."""
    clients = context.user_data.get("clients", [])
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

    sale = await crm.create_sale({
        "artwork_id": artwork["id"],
        "client_id": client_id,
        "sold_price": price,
    })
    await crm.update_artwork_status(artwork["id"], "sold")

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
        entry_points=[CommandHandler("sold", sold_start)],
        states={
            CHOOSE_BUYER: [
                CommandHandler("skip", skip_buyer),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_buyer),
            ],
            ENTER_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
