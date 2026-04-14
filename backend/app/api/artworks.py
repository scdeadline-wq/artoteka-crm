from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.models import Artwork, ArtworkStatus, Artist, Technique, Image, User
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate, ArtworkOut, ArtworkListOut
from app.services.storage import upload_image

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
