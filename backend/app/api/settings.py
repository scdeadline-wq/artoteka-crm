from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.currency import CURRENCY_SYMBOLS, normalize_currency
from app.database import get_db
from app.models import User
from app.schemas.setting import SettingsOut, SettingsUpdate
from app.services.settings import get_all_settings, set_settings

router = APIRouter()


def _to_out(values: dict[str, str]) -> SettingsOut:
    return SettingsOut(
        default_currency=normalize_currency(values.get("default_currency")),
        gallery_name=values.get("gallery_name") or "Артотека",
        pdf_logo_url=values.get("pdf_logo_url") or None,
        pdf_watermark_enabled=(values.get("pdf_watermark_enabled") or "").lower() == "true",
        pdf_watermark_text=values.get("pdf_watermark_text") or None,
        currencies=CURRENCY_SYMBOLS,
    )


@router.get("/", response_model=SettingsOut)
async def read_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _to_out(await get_all_settings(db))


@router.put("/", response_model=SettingsOut)
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    data = body.model_dump(exclude_unset=True)
    to_store: dict[str, str] = {}
    if "default_currency" in data and data["default_currency"] is not None:
        to_store["default_currency"] = normalize_currency(data["default_currency"])
    if "gallery_name" in data and data["gallery_name"] is not None:
        to_store["gallery_name"] = data["gallery_name"].strip()
    if "pdf_logo_url" in data:
        to_store["pdf_logo_url"] = (data["pdf_logo_url"] or "").strip()
    if "pdf_watermark_enabled" in data and data["pdf_watermark_enabled"] is not None:
        to_store["pdf_watermark_enabled"] = "true" if data["pdf_watermark_enabled"] else "false"
    if "pdf_watermark_text" in data:
        to_store["pdf_watermark_text"] = (data["pdf_watermark_text"] or "").strip()
    if to_store:
        await set_settings(db, to_store)
    return _to_out(await get_all_settings(db))
