"""Доступ к key-value настройкам приложения с дефолтами."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.currency import DEFAULT_CURRENCY, normalize_currency
from app.models.setting import AppSetting

DEFAULTS: dict[str, str] = {
    "default_currency": DEFAULT_CURRENCY,
    "gallery_name": "Артотека",
    "pdf_logo_url": "",
    "pdf_watermark_enabled": "false",
    "pdf_watermark_text": "",
}


async def get_all_settings(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    stored = {r.key: (r.value or "") for r in rows}
    merged = {**DEFAULTS, **stored}
    merged["default_currency"] = normalize_currency(merged.get("default_currency"))
    return merged


async def get_setting(db: AsyncSession, key: str) -> str:
    row = await db.get(AppSetting, key)
    if row is not None and row.value is not None:
        return row.value
    return DEFAULTS.get(key, "")


async def get_default_currency(db: AsyncSession) -> str:
    return normalize_currency(await get_setting(db, "default_currency"))


async def set_settings(db: AsyncSession, values: dict[str, str]) -> None:
    for key, value in values.items():
        row = await db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    await db.commit()
