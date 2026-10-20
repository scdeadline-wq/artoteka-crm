import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.models import Artwork, ArtworkStatus, ShareLink, User
from app.schemas.share import (
    ShareLinkCreate, ShareLinkUpdate, ShareLinkOut, PublicArtwork, PublicShareOut,
)

router = APIRouter()
public_router = APIRouter()

# Что видно по публичной ссылке: черновики, «на проверке» и проданные — нет
PUBLIC_STATUSES = (
    ArtworkStatus.for_sale,
    ArtworkStatus.reserved,
    ArtworkStatus.collection,
    ArtworkStatus.on_exhibition,
)
MAX_PUBLIC_ARTWORKS = 300


def _share_filter(stmt, link: ShareLink):
    if link.only_available:
        stmt = stmt.where(Artwork.status == ArtworkStatus.for_sale)
    else:
        stmt = stmt.where(Artwork.status.in_(PUBLIC_STATUSES))
    if link.artist_ids:
        stmt = stmt.where(Artwork.artist_id.in_(link.artist_ids))
    if link.tags:
        stmt = stmt.where(Artwork.tags.overlap(link.tags))
    return stmt


async def _count(db: AsyncSession, link: ShareLink) -> int:
    stmt = _share_filter(select(func.count(Artwork.id)), link)
    return (await db.execute(stmt)).scalar_one()


async def _to_out(db: AsyncSession, link: ShareLink) -> ShareLinkOut:
    out = ShareLinkOut.model_validate(link)
    out.artworks_count = await _count(db, link)
    return out


def _clean_tags(tags: list[str]) -> list[str]:
    seen: list[str] = []
    for t in tags:
        t = t.strip()
        if t and t not in seen:
            seen.append(t)
    return seen


@router.get("/", response_model=list[ShareLinkOut])
async def list_shares(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    links = (await db.execute(select(ShareLink).order_by(ShareLink.created_at.desc()))).scalars().all()
    return [await _to_out(db, link) for link in links]


@router.get("/tags/", response_model=list[str])
async def list_tags(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """Все теги каталога — для выбора в подборке."""
    tag = func.unnest(Artwork.tags).label("tag")
    rows = (await db.execute(select(tag).distinct().order_by(tag))).scalars().all()
    return [t for t in rows if t]


@router.post("/", response_model=ShareLinkOut, status_code=201)
async def create_share(
    body: ShareLinkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Без художников и тегов — весь каталог (например, «всё в наличии»)
    tags = _clean_tags(body.tags)
    link = ShareLink(
        token=secrets.token_urlsafe(16),
        title=body.title.strip(),
        artist_ids=sorted(set(body.artist_ids)),
        tags=tags,
        only_available=body.only_available,
        show_prices=body.show_prices,
        created_by_id=user.id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return await _to_out(db, link)


@router.patch("/{share_id}/", response_model=ShareLinkOut)
async def update_share(
    share_id: int,
    body: ShareLinkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    link = await db.get(ShareLink, share_id)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    for key, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(link, key, value.strip() if isinstance(value, str) else value)
    await db.commit()
    await db.refresh(link)
    return await _to_out(db, link)


@router.delete("/{share_id}/", status_code=204)
async def delete_share(
    share_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    link = await db.get(ShareLink, share_id)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    await db.delete(link)
    await db.commit()


@public_router.get("/shares/{token}/", response_model=PublicShareOut)
async def public_share(token: str, db: AsyncSession = Depends(get_db)):
    """Без авторизации: страница подборки для клиента."""
    link = (await db.execute(select(ShareLink).where(ShareLink.token == token))).scalar_one_or_none()
    if not link or not link.is_active:
        raise HTTPException(status_code=404, detail="Подборка не найдена или ссылка отключена")

    stmt = _share_filter(
        select(Artwork).options(
            selectinload(Artwork.artist),
            selectinload(Artwork.images),
            selectinload(Artwork.techniques),
        ),
        link,
    ).order_by(Artwork.created_at.desc()).limit(MAX_PUBLIC_ARTWORKS)
    artworks = (await db.execute(stmt)).scalars().all()

    out = []
    for aw in artworks:
        imgs = sorted(
            (i for i in aw.images if not i.is_internal),
            key=lambda i: (not i.is_primary, i.sort_order),
        )
        priced = link.show_prices and aw.status == ArtworkStatus.for_sale and aw.sale_price is not None
        out.append(PublicArtwork(
            id=aw.id,
            title=aw.title,
            artist_name=aw.artist.name_ru if aw.artist else None,
            year=aw.year_text or (str(aw.year) if aw.year else None),
            height_cm=float(aw.height_cm) if aw.height_cm is not None else None,
            width_cm=float(aw.width_cm) if aw.width_cm is not None else None,
            techniques=[t.name for t in aw.techniques],
            is_framed=aw.is_framed,
            description=aw.description,
            images=[i.url for i in imgs],
            is_reserved=aw.status == ArtworkStatus.reserved,
            sale_price=aw.sale_price if priced else None,
            currency=aw.currency if priced else None,
        ))
    return PublicShareOut(title=link.title, show_prices=link.show_prices, artworks=out)
