from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.models import Artwork, ArtworkStatus, Artist, Technique, Image, User
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate, ArtworkOut, ArtworkListOut
from fastapi.responses import Response as FastAPIResponse
from app.services.storage import upload_image, get_image_bytes
from app.services.ai import analyze_artwork_image
from app.services.enhance import auto_enhance, smart_crop
from app.services.mockup import generate_mockup, generate_custom_mockup
from app.models.mockup import Mockup

router = APIRouter()


async def _next_inventory_number(db: AsyncSession) -> int:
    result = await db.execute(select(func.coalesce(func.max(Artwork.inventory_number), 0)))
    return result.scalar() + 1


@router.get("/", response_model=list[ArtworkListOut])
async def list_artworks(
    status: str | None = None,
    artist_id: int | None = None,
    technique_id: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Artwork)
        .options(selectinload(Artwork.artist), selectinload(Artwork.images))
        .order_by(Artwork.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(Artwork.status == ArtworkStatus(status))
    if artist_id:
        stmt = stmt.where(Artwork.artist_id == artist_id)
    if technique_id:
        stmt = stmt.join(Artwork.techniques).where(Technique.id == technique_id)
    if year_from is not None:
        stmt = stmt.where(Artwork.year >= year_from)
    if year_to is not None:
        stmt = stmt.where(Artwork.year <= year_to)
    if q:
        from sqlalchemy import or_ as sa_or
        clauses = [
            Artwork.title.ilike(f"%{q}%"),
            Artwork.description.ilike(f"%{q}%"),
            Artwork.artist.has(Artist.name_ru.ilike(f"%{q}%")),
            Artwork.artist.has(Artist.name_en.ilike(f"%{q}%")),
        ]
        if q.strip().lstrip("№#").isdigit():
            clauses.append(Artwork.inventory_number == int(q.strip().lstrip("№#")))
        stmt = stmt.where(sa_or(*clauses))

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
        ))
    return out


@router.post("/", response_model=ArtworkOut, status_code=201)
async def create_artwork(
    body: ArtworkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = await db.get(Artist, body.artist_id)
    if not artist:
        raise HTTPException(status_code=400, detail="Artist not found")

    techniques = []
    if body.technique_ids:
        result = await db.execute(select(Technique).where(Technique.id.in_(body.technique_ids)))
        techniques = list(result.scalars().all())

    inv_num = await _next_inventory_number(db)
    data = body.model_dump(exclude={"technique_ids"})
    data["status"] = ArtworkStatus(data["status"])
    artwork = Artwork(**data, inventory_number=inv_num)
    artwork.techniques = techniques
    db.add(artwork)
    await db.commit()

    # Reload with relationships
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
        )
        .where(Artwork.id == artwork.id)
    )
    artwork = (await db.execute(stmt)).scalar_one()
    return artwork


@router.get("/{artwork_id}/", response_model=ArtworkOut)
async def get_artwork(
    artwork_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
        )
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return artwork


@router.put("/{artwork_id}/", response_model=ArtworkOut)
async def update_artwork(
    artwork_id: int,
    body: ArtworkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Artwork)
        .options(
            selectinload(Artwork.artist),
            selectinload(Artwork.techniques),
            selectinload(Artwork.images),
        )
        .where(Artwork.id == artwork_id)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    data = body.model_dump(exclude_unset=True)
    technique_ids = data.pop("technique_ids", None)

    if "status" in data:
        data["status"] = ArtworkStatus(data["status"])

    for key, value in data.items():
        setattr(artwork, key, value)

    if technique_ids is not None:
        result = await db.execute(select(Technique).where(Technique.id.in_(technique_ids)))
        artwork.techniques = list(result.scalars().all())

    await db.commit()
    await db.refresh(artwork)
    return artwork


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
    artwork.status = ArtworkStatus(status)
    await db.commit()
    return {"ok": True, "status": status}


@router.post("/{artwork_id}/images/")
async def upload_artwork_image(
    artwork_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artwork = await db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    url = await upload_image(file, artwork_id)
    image = Image(artwork_id=artwork_id, url=url, is_primary=is_primary)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return {"id": image.id, "url": image.url}


@router.post("/enhance-image/")
async def enhance_image_endpoint(
    file: UploadFile = File(...),
    crop: bool = True,
    _: User = Depends(get_current_user),
):
    """Улучшить фото: обрезка фона + авто-контраст/резкость."""
    image_bytes = await file.read()

    if crop:
        image_bytes = smart_crop(image_bytes)

    image_bytes = auto_enhance(image_bytes)

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
):
    """Генерирует мокап произведения в интерьере. Кеширует в MinIO."""
    import boto3
    from app.config import settings as cfg

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
