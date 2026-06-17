"""Поддерживаемые валюты и символы.

Без привязки к курсу: каждая цена/сделка хранит свой код валюты, конвертации нет.
Глобальный дефолт (admin) лежит в app_settings под ключом `default_currency`
и используется как стартовое значение в формах.
"""

DEFAULT_CURRENCY = "USD"

# Код → символ. Один источник правды для бэка/PDF (фронт и бот дублируют тот же список).
CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "RUB": "₽",
    "GBP": "£",
    "CNY": "¥",
}

SUPPORTED_CURRENCIES: list[str] = list(CURRENCY_SYMBOLS.keys())


def normalize_currency(value: str | None) -> str:
    """Привести к поддерживаемому коду, иначе вернуть дефолт."""
    if not value:
        return DEFAULT_CURRENCY
    code = value.strip().upper()
    return code if code in CURRENCY_SYMBOLS else DEFAULT_CURRENCY


def symbol(code: str | None) -> str:
    return CURRENCY_SYMBOLS.get(normalize_currency(code), "$")


def format_price(value, code: str | None) -> str:
    """`12000 $` — целое с пробелами-разделителями и символом валюты."""
    if value is None:
        return "—"
    try:
        amount = f"{int(float(value)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"
    return f"{amount} {symbol(code)}"
