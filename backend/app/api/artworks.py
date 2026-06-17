import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func, nullslast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.sorting import surname_expr
from app.auth import get_current_user, is_admin, require_admin
from app.currency import normalize_currency
from app.models import Artwork, ArtworkStatus, Artist, Technique, Image, Sale, User
from app.services.settings import get_default_currency, get_all_settings
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate, ArtworkOut, ArtworkListOut
from fastapi.responses import Response as FastAPIResponse
from app.services.storage import upload_image, get_image_bytes, delete_object
from app.services.ai import analyze_artwork_image
from app.services.enhance import auto_enhance, smart_crop
from app.services.mockup import generate_mockup, generate_custom_mockup
from app.services.pdf import render_artwork_pdf
from app.models.mockup import Mockup

router = APIRouter()


async def _next_inventory_number(db: AsyncSession) -> int:
    result = await db.execute(select(func.coalesce(func.max(Artwork.inventory_number), 0)))
    return result.scalar() + 1


def _mask_for_role(out: ArtworkOut, user: User) -> ArtworkOut:
    """purchase_price видна только админам (owner)."""
    if not is_admin(user):
        out.purchase_price = None
    return out


def _parse_status(value: str) -> ArtworkStatus:
    """Невалидный статус → 422 с перечнем допустимых, а не 500."""
    try:
        return ArtworkStatus(value)
    except ValueError:
        allowed = ", ".join(s.value for s in ArtworkStatus)
        raise HTTPException(
            status_code=422,
            detail=f"Недопустимый статус «{value}». Допустимые: {allowed}",
        )


def _escape_like(value: str) -> str:
    """Экранирует % и _ для ilike (escape='\\\\')."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _clear_reserve_fields(artwork: Artwork) -> None:
    artwork.reserved_client_id = None
    artwork.reserved_until = None
    artwork.reserve_note = None


@router.get("/", response_model=list[ArtworkListOut])
async def list_artworks(
    status: str | None = None,
    artist_id: int | None = None,
    technique_id: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    is_framed: bool | None = None,
    tag: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    room_id: int | None = None,
    warehouse_id: int | None = None,
    rack_id: int | None = None,
    shelf_id: int | None = None,
    q: str | None = None,
    sort: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.images),
            selectinload(Artwork.room),
        )
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(Artwork.status == _parse_status(status))
    if artist_id:
        stmt = stmt.where(Artwork.artist_id == artist_id)
    if technique_id:
        stmt = stmt.join(Artwork.techniques).where(Technique.id == technique_id)
    if year_from is not None:
        stmt = stmt.where(Artwork.year >= year_from)
    if year_to is not None:
        stmt = stmt.where(Artwork.year <= year_to)
    if is_framed is not None:
        stmt = stmt.where(Artwork.is_framed == is_framed)
    if tag:
        stmt = stmt.where(Artwork.tags.any(tag))
    if price_from is not None:
        stmt = stmt.where(Artwork.sale_price >= price_from)
    if price_to is not None:
        stmt = stmt.where(Artwork.sale_price <= price_to)
    if room_id is not None:
        stmt = stmt.where(Artwork.room_id == room_id)
    if warehouse_id is not None:
        stmt = stmt.where(Artwork.warehouse_id == warehouse_id)
    if rack_id is not None:
        stmt = stmt.where(Artwork.rack_id == rack_id)
    if shelf_id is not None:
        stmt = stmt.where(Artwork.shelf_id == shelf_id)
    if q:
        from sqlalchemy import or_ as sa_or
        q_clean = q.strip().lstrip("№#").strip()
        if q_clean.isdigit():
            stmt = stmt.where(Artwork.inventory_number == int(q_clean))
        else:
            q_like = f"%{_escape_like(q)}%"
            stmt = stmt.where(sa_or(
                Artwork.title.ilike(q_like, escape="\\"),
                Artwork.description.ilike(q_like, escape="\\"),
                Artwork.artist.has(Artist.name_ru.ilike(q_like, escape="\\")),
                Artwork.artist.has(Artist.name_en.ilike(q_like, escape="\\")),
            ))

    # Сортировка. По фамилии = последнее слово из artists.name_ru (формат «Имя Фамилия»).
    if sort == "last_name":
        stmt = stmt.join(Artwork.artist).order_by(
            surname_expr(Artist.name_ru),
            Artwork.inventory_number,
        )
    elif sort == "inventory":
        stmt = stmt.order_by(Artwork.inventory_number)
    elif sort == "price_asc":
        stmt = stmt.order_by(nullslast(Artwork.sale_price.asc()))
    elif sort == "price_desc":
        stmt = stmt.order_by(nullslast(Artwork.sale_price.desc()))
    else:
        stmt = stmt.order_by(Artwork.created_at.desc())

    results = (await db.execute(stmt)).scalars().all()
    out = []
    for aw in results:
        primary = next((img.url for img in aw.images if img.is_primary), None)
        if not primary and aw.images:
            primary = aw.images[0].url
        out.append(ArtworkListOut(
            id=aw.id,
            inventory_number=aw.inventory_number,
            title=aw.title,
            artist=aw.artist,
            status=aw.status.value,
            sale_price=aw.sale_price,
            primary_image=primary,
            year=aw.year,
            width_cm=float(aw.width_cm) if aw.width_cm is not None else None,
            height_cm=float(aw.height_cm) if aw.height_cm is not None else None,
            room=aw.room,
            is_framed=aw.is_framed,
            tags=list(aw.tags or []),
        ))
    return out


@router.get("/trash/")
async def list_trashed_artworks(
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Корзина — мягко удалённые работы. Только admin (owner)."""
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.images),
            selectinload(Artwork.room),
        )
        .where(Artwork.deleted_at.is_not(None))
        .order_by(Artwork.deleted_at.desc())
        .limit(limit)
        .offset(offset)
        .execution_options(include_deleted=True)
    )
    results = (await db.execute(stmt)).scalars().all()
    out = []
    for aw in results:
        primary = next((img.url for img in aw.images if img.is_primary), None)
        if not primary and aw.images:
            primary = aw.images[0].url
        out.append({
            "id": aw.id,
            "inventory_number": aw.inventory_number,
            "title": aw.title,
            "artist": {"id": aw.artist.id, "name_ru": aw.artist.name_ru, "name_en": aw.artist.name_en},
            "status": aw.status.value,
            "sale_price": float(aw.sale_price) if aw.sale_price is not None else None,
            "primary_image": primary,
            "year": aw.year,
            "room": {"id": aw.room.id, "name": aw.room.name, "sort_order": aw.room.sort_order} if aw.room else None,
            "deleted_at": aw.deleted_at.isoformat() if aw.deleted_at else None,
        })
    return out


@router.post("/", response_model=ArtworkOut, status_code=201)
async def create_artwork(
    body: ArtworkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    artist = await db.get(Artist, body.artist_id)
    if not artist:
        raise HTTPException(status_code=400, detail="Artist not found")

    techniques = []
    if body.technique_ids:
        result = await db.execute(select(Technique).where(Technique.id.in_(body.technique_ids)))
        techniques = list(result.scalars().all())

    data = body.model_dump(exclude={"technique_ids"})
    data["status"] = _parse_status(data["status"])
    # Валюта: явная → дефолт из настроек
    data["currency"] = normalize_currency(data.get("currency")) if data.get("currency") else await get_default_currency(db)
    # purchase_price может задавать только admin
    if not is_admin(user):
        data.pop("purchase_price", None)

    # Инв. номер = max+1 → возможна гонка на unique-индексе. Ретраим до 3 раз.
    for attempt in range(3):
        inv_num = await _next_inventory_number(db)
        artwork = Artwork(**data, inventory_number=inv_num)
        artwork.techniques = list(techniques)
        db.add(artwork)
        try:
            await db.commit()
            break
        except IntegrityError:
            await db.rollback()
            if attempt == 2:
                raise HTTPException(
                    status_code=409,
                    detail="Не удалось выдать инвентарный номер (конфликт), попробуйте ещё раз",
                )
            # rollback экспайрит объекты сессии — перечитываем техники
            if body.technique_ids:
                result = await db.execute(select(Technique).where(Technique.id.in_(body.technique_ids)))
                techniques = list(result.scalars().all())

    # Reload with relationships
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
            selectinload(Artwork.room),
            selectinload(Artwork.warehouse),
            selectinload(Artwork.rack),
            selectinload(Artwork.shelf),
        )
        .where(Artwork.id == artwork.id)
    )
    artwork = (await db.execute(stmt)).scalar_one()
    return _mask_for_role(ArtworkOut.model_validate(artwork), user)


@router.get("/{artwork_id}/", response_model=ArtworkOut)
async def get_artwork(
    artwork_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
            selectinload(Artwork.room),
            selectinload(Artwork.warehouse),
            selectinload(Artwork.rack),
            selectinload(Artwork.shelf),
        )
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return _mask_for_role(ArtworkOut.model_validate(artwork), user)


@router.put("/{artwork_id}/", response_model=ArtworkOut)
async def update_artwork(
    artwork_id: int,
    body: ArtworkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
            selectinload(Artwork.room),
            selectinload(Artwork.warehouse),
            selectinload(Artwork.rack),
            selectinload(Artwork.shelf),
        )
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    data = body.model_dump(exclude_unset=True)
    technique_ids = data.pop("technique_ids", None)

    if "status" in data:
        data["status"] = _parse_status(data["status"])

    # Валюта: нормализуем; пустую не затираем (колонка non-nullable)
    if "currency" in data:
        if data["currency"]:
            data["currency"] = normalize_currency(data["currency"])
        else:
            data.pop("currency")

    # Менять purchase_price может только admin
    if not is_admin(user):
        data.pop("purchase_price", None)

    # Снимаем резерв при смене статуса с reserved на любой другой
    if (
        "status" in data
        and artwork.status == ArtworkStatus.reserved
        and data["status"] != ArtworkStatus.reserved
    ):
        data["reserved_client_id"] = None
        data["reserved_until"] = None
        data["reserve_note"] = None

    for key, value in data.items():
        setattr(artwork, key, value)

    if technique_ids is not None:
        result = await db.execute(select(Technique).where(Technique.id.in_(technique_ids)))
        artwork.techniques = list(result.scalars().all())

    await db.commit()
    await db.refresh(artwork)
    return _mask_for_role(ArtworkOut.model_validate(artwork), user)


@router.delete("/{artwork_id}/", status_code=200)
async def soft_delete_artwork(
    artwork_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """Мягкое удаление — работа помечается deleted_at, физически не стирается.
    Восстановить через POST /artworks/{id}/restore/, посмотреть удалённые — GET /artworks/trash/.
    """
    stmt = (
        select(Artwork)
        .where(Artwork.id == artwork_id)
        .execution_options(include_deleted=True)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    if artwork.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Already deleted")
    sales_count = (
        await db.execute(select(func.count(Sale.id)).where(Sale.artwork_id == artwork_id))
    ).scalar()
    if sales_count:
        raise HTTPException(
            status_code=409,
            detail="Нельзя удалить работу: по ней оформлена продажа. Сначала отмените продажу.",
        )
    artwork.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "id": artwork_id, "deleted_at": artwork.deleted_at.isoformat()}


@router.post("/{artwork_id}/restore/", status_code=200)
async def restore_artwork(
    artwork_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    stmt = (
        select(Artwork)
        .where(Artwork.id == artwork_id)
        .execution_options(include_deleted=True)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    if artwork.deleted_at is None:
        raise HTTPException(status_code=400, detail="Not deleted")
    artwork.deleted_at = None
    await db.commit()
    return {"ok": True, "id": artwork_id}


@router.post("/analyze-image/")
async def analyze_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-анализ фото: возвращает предзаполненные поля для карточки."""
    image_bytes = await file.read()
    ai_result = await analyze_artwork_image(image_bytes, file.content_type)

    if "error" in ai_result:
        raise HTTPException(status_code=500, detail=ai_result["error"])

    # Сматчим техники из AI с нашим справочником
    technique_names = ai_result.get("techniques") or []
    matched_techniques = []
    if technique_names:
        result = await db.execute(select(Technique).where(Technique.name.in_(technique_names)))
        matched_techniques = [{"id": t.id, "name": t.name} for t in result.scalars().all()]

    # Сматчим художника если AI его узнал
    artist_match = None
    artist_name = ai_result.get("artist_name")
    if artist_name:
        result = await db.execute(
            select(Artist).where(
                Artist.name_ru.ilike(f"%{artist_name}%")
                | Artist.name_en.ilike(f"%{artist_name}%")
            )
        )
        found = result.scalar_one_or_none()
        if found:
            artist_match = {"id": found.id, "name_ru": found.name_ru, "name_en": found.name_en}

    return {
        "ai_raw": ai_result,
        "sources": ai_result.get("_sources") or [],
        "suggested": {
            "title": ai_result.get("title"),
            "artist": artist_match,
            "artist_name_suggestion": artist_name,
            "year": _parse_year(ai_result.get("year_estimate")),
            "techniques": matched_techniques,
            "description": ai_result.get("description"),
            "condition": ai_result.get("condition"),
            "style_period": ai_result.get("style_period"),
            "tags": ai_result.get("tags") or [],
            "width_cm": _parse_float(ai_result.get("width_cm")),
            "height_cm": _parse_float(ai_result.get("height_cm")),
            "estimated_price_rub": ai_result.get("estimated_price_rub"),
            "confidence": ai_result.get("confidence"),
        },
    }


def _parse_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _parse_year(year_str: str | None) -> int | None:
    if not year_str:
        return None
    # "1967" -> 1967, "1960-е" -> 1960
    digits = "".join(c for c in str(year_str) if c.isdigit())
    return int(digits[:4]) if len(digits) >= 4 else None


@router.get("/{artwork_id}/pdf/")
async def artwork_pdf(
    artwork_id: int,
    include_provenance: bool = True,
    include_purchase_price: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PDF-карточка работы для клиента. Тумблеры (провенанс, закупочная цена),
    лого и водяной знак берутся из настроек. Закупочная цена — только admin."""
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
            selectinload(Artwork.room),
            selectinload(Artwork.warehouse),
            selectinload(Artwork.rack),
            selectinload(Artwork.shelf),
        )
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    # Закупочную цену показываем только админам и только если явно попросили (по умолчанию — да для admin)
    show_purchase = is_admin(user) and (include_purchase_price is not False)

    cfg = await get_all_settings(db)
    watermark = None
    if (cfg.get("pdf_watermark_enabled") or "").lower() == "true":
        watermark = cfg.get("pdf_watermark_text") or cfg.get("gallery_name") or "Артотека"

    # weasyprint — синхронный и тяжёлый, не блокируем event loop
    pdf_bytes = await asyncio.to_thread(
        render_artwork_pdf,
        artwork,
        include_purchase_price=show_purchase,
        include_provenance=include_provenance,
        gallery_name=cfg.get("gallery_name") or "Артотека",
        logo_url=cfg.get("pdf_logo_url") or None,
        watermark_text=watermark,
    )
    inv = artwork.inventory_number
    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="artoteka_{inv}.pdf"'},
    )


@router.patch("/{artwork_id}/status/")
async def change_status(
    artwork_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artwork = await db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    new_status = _parse_status(status)
    # Снимаем резерв при смене статуса с reserved на любой другой
    if artwork.status == ArtworkStatus.reserved and new_status != ArtworkStatus.reserved:
        _clear_reserve_fields(artwork)
    artwork.status = new_status
    await db.commit()
    return {"ok": True, "status": status}


@router.post("/{artwork_id}/images/")
async def upload_artwork_image(
    artwork_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    is_internal: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artwork = await db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    url = await upload_image(file, artwork_id)
    # Внутреннее фото (сертификат, оборот) не может быть главным
    image = Image(artwork_id=artwork_id, url=url, is_primary=is_primary and not is_internal, is_internal=is_internal)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return {"id": image.id, "url": image.url, "is_internal": image.is_internal}


@router.delete("/{artwork_id}/images/{image_id}/", status_code=204)
async def delete_artwork_image(
    artwork_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Удалить фото работы (и файл из MinIO). Если удалили primary —
    primary становится первое оставшееся фото."""
    stmt = select(Image).where(Image.id == image_id, Image.artwork_id == artwork_id)
    image = (await db.execute(stmt)).scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    was_primary = image.is_primary
    key = image.url.replace("/images/", "", 1)
    await db.delete(image)
    await db.flush()

    if was_primary:
        rest_stmt = (
            select(Image)
            .where(Image.artwork_id == artwork_id)
            .order_by(Image.sort_order, Image.id)
        )
        rest = (await db.execute(rest_stmt)).scalars().all()
        if rest:
            rest[0].is_primary = True

    await db.commit()

    # Файл из MinIO — после успешного коммита; ошибка стораджа не должна ронять запрос
    try:
        await asyncio.to_thread(delete_object, key)
    except Exception:
        pass
    return FastAPIResponse(status_code=204)


@router.patch("/{artwork_id}/images/{image_id}/")
async def update_artwork_image(
    artwork_id: int,
    image_id: int,
    is_primary: bool | None = Query(None),
    is_internal: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Сделать фото главным (is_primary=true, снимает primary с остальных) и/или
    пометить как внутреннее (is_internal — не попадает в клиентский PDF)."""
    stmt = select(Image).where(Image.id == image_id, Image.artwork_id == artwork_id)
    image = (await db.execute(stmt)).scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if is_internal is not None:
        image.is_internal = is_internal
        if is_internal:
            image.is_primary = False  # внутреннее фото не может быть главным
    if is_primary is not None and is_primary and not image.is_internal:
        others_stmt = select(Image).where(Image.artwork_id == artwork_id, Image.id != image_id)
        for other in (await db.execute(others_stmt)).scalars().all():
            other.is_primary = False
        image.is_primary = True
    elif is_primary is False:
        image.is_primary = False
    await db.commit()
    return {"id": image.id, "url": image.url, "is_primary": image.is_primary, "is_internal": image.is_internal}


@router.post("/enhance-image/")
async def enhance_image_endpoint(
    file: UploadFile = File(...),
    crop: bool = True,
    _: User = Depends(get_current_user),
):
    """Улучшить фото: обрезка фона + авто-контраст/резкость."""
    image_bytes = await file.read()

    # PIL-обработка синхронная и тяжёлая — не блокируем event loop
    if crop:
        image_bytes = await asyncio.to_thread(smart_crop, image_bytes)

    image_bytes = await asyncio.to_thread(auto_enhance, image_bytes)

    return FastAPIResponse(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Content-Disposition": "inline; filename=enhanced.jpg"},
    )


@router.get("/{artwork_id}/mockup/")
async def get_mockup(
    artwork_id: int,
    style: str = "office",
    t: str = "",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Генерирует мокап произведения в интерьере. Кеширует в MinIO."""
    import boto3
    from app.config import settings as cfg
    from app.services.mockup import ROOM_PROMPTS

    if style not in ROOM_PROMPTS:
        allowed = ", ".join(ROOM_PROMPTS)
        raise HTTPException(
            status_code=422,
            detail=f"Недопустимый стиль «{style}». Допустимые: {allowed}",
        )

    # Проверяем кеш в MinIO
    cache_key = f"mockups/{artwork_id}/{style}.jpg"
    s3 = boto3.client("s3", endpoint_url=cfg.s3_endpoint, aws_access_key_id=cfg.s3_access_key, aws_secret_access_key=cfg.s3_secret_key)
    try:
        cached = s3.get_object(Bucket=cfg.s3_bucket, Key=cache_key)
        return FastAPIResponse(
            content=cached["Body"].read(),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400", "X-Cache": "HIT"},
        )
    except s3.exceptions.NoSuchKey:
        pass

    stmt = (
        select(Artwork)
        .options(selectinload(Artwork.images))
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    primary = next((img for img in artwork.images if img.is_primary), None)
    if not primary and artwork.images:
        primary = artwork.images[0]
    if not primary:
        raise HTTPException(status_code=400, detail="No images for this artwork")

    key = primary.url.replace("/images/", "", 1)
    image_data, _ = get_image_bytes(key)

    mockup_bytes = await generate_mockup(
        image_data,
        style,
        width_cm=float(artwork.width_cm) if artwork.width_cm else None,
        height_cm=float(artwork.height_cm) if artwork.height_cm else None,
    )

    # Сохраняем в кеш
    s3.put_object(Bucket=cfg.s3_bucket, Key=cache_key, Body=mockup_bytes, ContentType="image/jpeg")

    return FastAPIResponse(
        content=mockup_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400", "X-Cache": "MISS"},
    )


@router.post("/{artwork_id}/custom-mockup/")
async def custom_mockup(
    artwork_id: int,
    room_photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Персональный мокап: фото комнаты клиента + произведение."""
    stmt = (
        select(Artwork)
        .options(selectinload(Artwork.images))
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    primary = next((img for img in artwork.images if img.is_primary), None)
    if not primary and artwork.images:
        primary = artwork.images[0]
    if not primary:
        raise HTTPException(status_code=400, detail="No images for this artwork")

    key = primary.url.replace("/images/", "", 1)
    artwork_data, _ = get_image_bytes(key)
    room_data = await room_photo.read()

    result = await generate_custom_mockup(
        room_data,
        artwork_data,
        width_cm=float(artwork.width_cm) if artwork.width_cm else None,
        height_cm=float(artwork.height_cm) if artwork.height_cm else None,
    )

    # Сохраняем в MinIO
    import uuid
    import boto3
    from app.config import settings as cfg
    from app.services.image_utils import normalize_image

    s3 = boto3.client("s3", endpoint_url=cfg.s3_endpoint, aws_access_key_id=cfg.s3_access_key, aws_secret_access_key=cfg.s3_secret_key)
    uid = uuid.uuid4().hex

    room_key = f"mockups/custom/{uid}_room.jpg"
    s3.put_object(Bucket=cfg.s3_bucket, Key=room_key, Body=normalize_image(room_data), ContentType="image/jpeg")

    result_key = f"mockups/custom/{uid}_result.jpg"
    s3.put_object(Bucket=cfg.s3_bucket, Key=result_key, Body=result, ContentType="image/jpeg")

    mockup = Mockup(
        artwork_id=artwork_id,
        room_image_url=f"/images/{room_key}",
        result_image_url=f"/images/{result_key}",
        style="custom",
    )
    db.add(mockup)
    await db.commit()
    await db.refresh(mockup)

    return {
        "id": mockup.id,
        "result_url": mockup.result_image_url,
        "room_url": mockup.room_image_url,
        "artwork_id": artwork_id,
    }


@router.get("/mockups/history/")
async def mockup_history(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """История всех персональных мокапов."""
    stmt = (
        select(Mockup)
        .options(selectinload(Mockup.artwork).selectinload(Artwork.artist))
        .where(Mockup.style == "custom")
        .order_by(Mockup.created_at.desc())
        .limit(50)
    )
    mockups = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": m.id,
            "artwork_id": m.artwork_id,
            "artwork_title": m.artwork.title if m.artwork else None,
            "artist_name": m.artwork.artist.name_ru if m.artwork and m.artwork.artist else None,
            "room_url": m.room_image_url,
            "result_url": m.result_image_url,
            "created_at": m.created_at.isoformat(),
        }
        for m in mockups
    ]
