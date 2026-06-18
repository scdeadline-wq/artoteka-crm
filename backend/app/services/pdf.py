"""Рендер карточки произведения в PDF через weasyprint.

Принимает уже загруженный объект Artwork со всеми relationship'ами
(artist, techniques, images, room). Первичную (не-внутреннюю) картинку
встраивает в PDF как base64-dataURL.

PDF — артефакт для клиента, поэтому настраивается: что включать (провенанс,
закупочную цену), логотип галереи и водяной знак. Внутренние фото (is_internal)
в клиентский PDF не попадают.
"""
from __future__ import annotations

import base64
import logging
from html import escape
from io import BytesIO

from weasyprint import HTML

from app.currency import symbol as currency_symbol
from app.models.artwork import Artwork
from app.services.storage import get_image_bytes

log = logging.getLogger(__name__)


def _fetch_data_url(url: str) -> str | None:
    key = (url or "").lstrip("/").replace("images/", "", 1)
    if not key:
        return None
    try:
        data, ct = get_image_bytes(key)
    except Exception as e:
        log.warning("PDF: не удалось загрузить картинку %r: %s", url, e)
        return None
    return f"data:{ct};base64,{base64.b64encode(data).decode()}"


def _image_data_url(artwork: Artwork) -> str | None:
    # В клиентский PDF — только не-внутренние фото
    images = [i for i in (artwork.images or []) if not getattr(i, "is_internal", False)]
    images.sort(key=lambda i: (not i.is_primary, i.sort_order))
    if not images:
        return None
    return _fetch_data_url(images[0].url or "")


def _logo_data_url(logo_url: str | None) -> str | None:
    if not logo_url:
        return None
    # Внешний URL: пробуем скачать сами и встроить как data-url. Если не вышло
    # (гео-блок, не картинка, напр. ссылка Google Drive «.../view») — None → в шапке покажется название галереи.
    if logo_url.startswith("http://") or logo_url.startswith("https://"):
        try:
            import urllib.request
            req = urllib.request.Request(logo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                ct = r.headers.get("Content-Type", "")
                if not ct.startswith("image/"):
                    return None
                data = r.read()
            return f"data:{ct};base64,{base64.b64encode(data).decode()}"
        except Exception as e:
            log.warning("PDF: не удалось загрузить внешний логотип %r: %s", logo_url, e)
            return None
    # Внутренний путь (/images/...) — через наш storage
    return _fetch_data_url(logo_url)


def _fmt_price(value, currency: str | None) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{int(float(value)):,} {currency_symbol(currency)}".replace(",", " ")
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
    "on_exhibition": "На выставке",
}


def _html(
    artwork: Artwork,
    *,
    include_sale_price: bool,
    include_provenance: bool,
    gallery_name: str,
    logo_url: str | None,
    watermark_text: str | None,
) -> str:
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
    provenance = (artwork.provenance or "") if include_provenance else ""
    edition = artwork.edition or "—"
    condition = artwork.condition or "—"
    year = artwork.year or "—"
    cur = artwork.currency

    img = _image_data_url(artwork)
    img_block = (
        f'<img class="image" src="{img}" alt=""/>'
        if img
        else '<div class="image-stub">— нет фото —</div>'
    )

    logo = _logo_data_url(logo_url)
    logo_block = f'<img class="logo" src="{logo}" alt=""/>' if logo else escape(gallery_name)

    watermark_block = (
        f'<div class="watermark">{escape(watermark_text)}</div>' if watermark_text else ''
    )

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 1.8cm; }}
  body {{ font-family: 'DejaVu Sans', sans-serif; color: #1f2937; position: relative; }}
  .watermark {{
    position: fixed; top: 45%; left: 0; right: 0; text-align: center;
    font-size: 60pt; color: rgba(0,0,0,0.06); transform: rotate(-30deg);
    z-index: 0; font-weight: bold;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #d1d5db; padding-bottom: 8px; margin-bottom: 20px;
    font-size: 9pt; color: #6b7280;
  }}
  .logo {{ max-height: 1.2cm; max-width: 5cm; }}
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
  .content {{ position: relative; z-index: 1; }}
</style></head><body>
  {watermark_block}
  <div class="content">
  <div class="header">
    <span class="inv">№ {escape(str(artwork.inventory_number))}</span>
    <span>{logo_block}</span>
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
  </dl>

  {f'<div class="desc-title">Описание</div><div class="desc">{escape(description)}</div>' if description else ''}

  {f'<div class="desc-title">Провенанс</div><div class="desc">{escape(provenance)}</div>' if provenance else ''}

  {f'<div class="price">Цена продажи: {escape(_fmt_price(artwork.sale_price, cur))}</div>' if (include_sale_price and artwork.sale_price) else ''}

  <div class="footer">{escape(gallery_name)}</div>
  </div>
</body></html>"""


def render_artwork_pdf(
    artwork: Artwork,
    *,
    include_sale_price: bool = True,
    include_provenance: bool = True,
    gallery_name: str = "Артотека",
    logo_url: str | None = None,
    watermark_text: str | None = None,
) -> bytes:
    html_str = _html(
        artwork,
        include_sale_price=include_sale_price,
        include_provenance=include_provenance,
        gallery_name=gallery_name,
        logo_url=logo_url,
        watermark_text=watermark_text,
    )
    buf = BytesIO()
    HTML(string=html_str).write_pdf(buf)
    return buf.getvalue()
