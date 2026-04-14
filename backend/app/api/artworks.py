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
from app.services.mockup import generate_mockup

router = APIRouter()


async def _next_inventory_number(db: AsyncSession) -> int:
    result = await db.execute(select(func.coalesce(func.max(Artwork.inventory_number), 0)))
    return result.scalar() + 1


@router.get("/", response_model=list[ArtworkListOut])
async def list_artworks(
    status: str | None = None,
    artist_id: int | None = None,
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
    if q:
        stmt = stmt.where(
            Artwork.title.ilike(f"%{q}%")
            | Artwork.description.ilike(f"%{q}%")
        )

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


@router.get("/{artwork_id}", response_model=ArtworkOut)
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


@router.put("/{artwork_id}", response_model=ArtworkOut)
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


@router.post("/analyze-image")
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
            "estimated_price_rub": ai_result.get("estimated_price_rub"),
            "confidence": ai_result.get("confidence"),
        },
    }


def _parse_year(year_str: str | None) -> int | None:
    if not year_str:
        return None
    # "1967" -> 1967, "1960-е" -> 1960
    digits = "".join(c for c in str(year_str) if c.isdigit())
    return int(digits[:4]) if len(digits) >= 4 else None


@router.patch("/{artwork_id}/status")
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


@router.post("/{artwork_id}/images")
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


@router.post("/enhance-image")
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


@router.get("/{artwork_id}/mockup")
async def get_mockup(
    artwork_id: int,
    style: str = "office",
    t: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Генерирует мокап произведения в интерьере."""
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

    # Загружаем изображение из S3
    key = primary.url.replace("/images/", "", 1)
    image_data, _ = get_image_bytes(key)

    mockup_bytes = await generate_mockup(image_data, style)

    return FastAPIResponse(
        content=mockup_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )
