from pydantic import BaseModel


class SettingsOut(BaseModel):
    """Все настройки приложения одним словарём + справочник валют для UI."""

    default_currency: str
    gallery_name: str
    pdf_logo_url: str | None = None
    pdf_watermark_enabled: bool = False
    pdf_watermark_text: str | None = None
    currencies: dict[str, str]  # код → символ


class SettingsUpdate(BaseModel):
    default_currency: str | None = None
    gallery_name: str | None = None
    pdf_logo_url: str | None = None
    pdf_watermark_enabled: bool | None = None
    pdf_watermark_text: str | None = None
