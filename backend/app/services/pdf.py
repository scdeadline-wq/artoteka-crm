"""Рендер карточки произведения в PDF через weasyprint.

Принимает уже загруженный объект Artwork со всеми relationship'ами
(artist, techniques, images, room). Картинку первичную (или первую)
встраивает в PDF как base64-dataURL.
"""
from __future__ import annotations

import base64
import logging
from html import escape
from io import BytesIO

from weasyprint import HTML

from app.models.artwork import Artwork
from app.services.storage import get_image_bytes

log = logging.getLogger(__name__)


def _image_data_url(artwork: Artwork) -> str | None:
    images = sorted(
        artwork.images or [],
        key=lambda i: (not i.is_primary, i.sort_order),
    )
    if not images:
        return None
    primary = images[0]
    url = primary.url or ""
    key = url.lstrip("/").replace("images/", "", 1)
    try:
        data, ct = get_image_bytes(key)
    except Exception as e:
        log.warning("PDF: не удалось загрузить картинку %r: %s", url, e)
        return None
    return f"data:{ct};base64,{base64.b64encode(data).decode()}"


def _fmt_price(value) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{int(float(value)):,} ₽".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _fmt_size(artwork: Artwork) -> str:
    w = artwork.width_cm
    h = artwork.height_cm
    if w and h:
        return f"{w} × {h} см"
    if w:
        return f"{w} см (ширина)"
    if h:
        return f"{h} см (высота)"
    return "—"


STATUS_LABELS = {
    "draft": "Черновик",
    "review": "На проверке",
    "for_sale": "В продаже",
    "reserved": "Зарезервирована",
    "sold": "Продана",
    "collection": "В коллекции",
}


def _html(artwork: Artwork, *, include_purchase_price: bool) -> str:
    artist = artwork.artist
    artist_name = (artist.name_ru if artist else None) or "—"
    artist_en = (artist.name_en if artist else None) or ""
    title = artwork.title or "Без названия"
    techs = ", ".join(t.name for t in (artwork.techniques or [])) or "—"
    size = _fmt_size(artwork)
    framed = "В раме" if artwork.is_framed else "Без рамы"
    status = STATUS_LABELS.get(artwork.status.value if hasattr(artwork.status, "value") else artwork.status, "—")
    room = artwork.room.name if artwork.room else "—"
    tags = " ".join(f"#{t}" for t in (artwork.tags or [])) or "—"
    description = artwork.description or ""
    edition = artwork.edition or "—"
    condition = artwork.condition or "—"
    year = artwork.year or "—"

    img = _image_data_url(artwork)
    img_block = (
        f'<img class="image" src="{img}" alt=""/>'
        if img
        else '<div class="image-stub">— нет фото —</div>'
    )

    purchase_block = ""
    if include_purchase_price and artwork.purchase_price is not None:
        purchase_block = (
            f'<dt>Закупочная цена</dt>'
            f'<dd>{escape(_fmt_price(artwork.purchase_price))}</dd>'
        )

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 1.8cm; }}
  body {{ font-family: 'DejaVu Sans', sans-serif; color: #1f2937; }}
  .header {{
    display: flex; justify-content: space-between;
    border-bottom: 1px solid #d1d5db; padding-bottom: 8px; margin-bottom: 20px;
    font-size: 9pt; color: #6b7280;
  }}
  .inv {{ font-size: 11pt; font-weight: bold; color: #111827; letter-spacing: 0.5px; }}
  .image {{ display: block; max-width: 100%; max-height: 11cm; margin: 0 auto 16px; }}
  .image-stub {{
    height: 6cm; display: flex; align-items: center; justify-content: center;
    background: #f3f4f6; color: #9ca3af; margin-bottom: 16px; border-radius: 4px;
  }}
  .artist {{ font-size: 20pt; font-weight: bold; margin: 12px 0 2px; color: #111827; }}
  .artist-en {{ font-size: 11pt; color: #6b7280; margin-bottom: 6px; }}
  .title {{ font-size: 14pt; color: #374151; font-style: italic; margin-bottom: 18px; }}
  .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; margin-bottom: 16px; }}
  dt {{ color: #6b7280; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.3px; margin-top: 6px; }}
  dd {{ font-size: 11pt; margin: 0; color: #111827; }}
  .desc-title {{ color: #6b7280; font-size: 8pt; text-transform: uppercase; margin: 20px 0 4px; }}
  .desc {{ font-size: 10pt; line-height: 1.5; color: #374151; }}
  .price {{
    margin-top: 24px; padding: 12px; background: #ecfdf5; border-left: 3px solid #10b981;
    font-size: 14pt; font-weight: bold; color: #047857;
  }}
  .footer {{
    margin-top: 32px; padding-top: 10px; border-top: 1px solid #e5e7eb;
    font-size: 8pt; color: #9ca3af; text-align: center;
  }}
</style></head><body>
  <div class="header">
    <span class="inv">№ {escape(str(artwork.inventory_number))}</span>
    <span>{escape(status)} · Комната: {escape(room)}</span>
  </div>

  {img_block}

  <div class="artist">{escape(artist_name)}</div>
  {f'<div class="artist-en">{escape(artist_en)}</div>' if artist_en else ''}
  <div class="title">{escape(title)}</div>

  <dl class="meta">
    <div><dt>Год</dt><dd>{escape(str(year))}</dd></div>
    <div><dt>Размер</dt><dd>{escape(size)}</dd></div>
    <div><dt>Техника</dt><dd>{escape(techs)}</dd></div>
    <div><dt>Тираж</dt><dd>{escape(edition)}</dd></div>
    <div><dt>Состояние</dt><dd>{escape(condition)}</dd></div>
    <div><dt>Оформление</dt><dd>{escape(framed)}</dd></div>
    {f'<div><dt>Теги</dt><dd>{escape(tags)}</dd></div>' if artwork.tags else ''}
    {f'<div>{purchase_block}</div>' if purchase_block else ''}
  </dl>

  {f'<div class="desc-title">Описание</div><div class="desc">{escape(description)}</div>' if description else ''}

  {f'<div class="price">Цена продажи: {escape(_fmt_price(artwork.sale_price))}</div>' if artwork.sale_price else ''}

  <div class="footer">Артотека CRM</div>
</body></html>"""


def render_artwork_pdf(artwork: Artwork, *, include_purchase_price: bool) -> bytes:
    html_str = _html(artwork, include_purchase_price=include_purchase_price)
    buf = BytesIO()
    HTML(string=html_str).write_pdf(buf)
    return buf.getvalue()
