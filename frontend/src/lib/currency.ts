// Валюты без привязки к курсу: каждая цена хранит свой код.
// Дефолтный код приходит из настроек (/settings), символы — отсюда.

export const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  RUB: "₽",
  GBP: "£",
  CNY: "¥",
};

export const SUPPORTED_CURRENCIES = Object.keys(CURRENCY_SYMBOLS);

export const DEFAULT_CURRENCY = "USD";

export function currencySymbol(code: string | null | undefined): string {
  if (!code) return CURRENCY_SYMBOLS[DEFAULT_CURRENCY];
  return CURRENCY_SYMBOLS[code.toUpperCase()] || code;
}

// "12 000 $" — целое с неразрывными пробелами + символ валюты
export function formatPrice(
  value: number | string | null | undefined,
  code: string | null | undefined
): string {
  if (value == null || value === "") return "—";
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return "—";
  return `${Math.round(num).toLocaleString("ru")} ${currencySymbol(code)}`;
}
