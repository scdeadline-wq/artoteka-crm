from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models import Artist, User
from app.schemas.artist import ArtistCreate, ArtistUpdate, ArtistOut

router = APIRouter()


@router.get("/", response_model=list[ArtistOut])
async def list_artists(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Artist).order_by(Artist.name_ru)
    if q:
        stmt = stmt.where(Artist.name_ru.ilike(f"%{q}%") | Artist.name_en.ilike(f"%{q}%"))
    return (await db.execute(stmt)).scalars().all()


@router.post("/", response_model=ArtistOut, status_code=201)
async def create_artist(
    body: ArtistCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = Artist(**body.model_dump())
    db.add(artist)
    await db.commit()
    await db.refresh(artist)
    return artist


@router.get("/{artist_id}/", response_model=ArtistOut)
async def get_artist(
    artist_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist


@router.put("/{artist_id}/", response_model=ArtistOut)
async def update_artist(
    artist_id: int,
    body: ArtistUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(artist, key, value)
    await db.commit()
    await db.refresh(artist)
    return artist
