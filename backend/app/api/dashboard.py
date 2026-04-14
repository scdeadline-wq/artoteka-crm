from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models import Sale, Artwork, ArtworkStatus, Artist, User

router = APIRouter()


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Общая выручка и кол-во продаж
    sales_result = await db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.sold_price), 0))
    )
    total_sales, total_revenue = sales_result.one()

    # Общие закупки
    purchase_result = await db.execute(
        select(func.coalesce(func.sum(Artwork.purchase_price), 0))
        .where(Artwork.status == ArtworkStatus.sold)
    )
    total_purchase = purchase_result.scalar()

    # Реферальные выплаты
    ref_result = await db.execute(
        select(func.coalesce(func.sum(Sale.referral_fee), 0))
    )
    total_referral_fees = ref_result.scalar()

    # Работы по статусам
    status_result = await db.execute(
        select(Artwork.status, func.count(Artwork.id)).group_by(Artwork.status)
    )
    statuses = {row[0].value: row[1] for row in status_result.all()}

    margin = Decimal(str(total_revenue)) - Decimal(str(total_purchase)) - Decimal(str(total_referral_fees))

    return {
        "total_sales": total_sales,
        "total_revenue": float(total_revenue),
        "total_purchase": float(total_purchase),
        "total_referral_fees": float(total_referral_fees),
        "margin": float(margin),
        "artworks_by_status": statuses,
    }


@router.get("/top-artists")
async def top_artists(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(
            Artist.id,
            Artist.name_ru,
            func.count(Sale.id).label("sales_count"),
            func.coalesce(func.sum(Sale.sold_price), 0).label("total_revenue"),
        )
        .join(Artwork, Artwork.artist_id == Artist.id)
        .join(Sale, Sale.artwork_id == Artwork.id)
        .group_by(Artist.id)
        .order_by(func.sum(Sale.sold_price).desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "artist_id": r[0],
            "name": r[1],
            "sales_count": r[2],
            "total_revenue": float(r[3]),
        }
        for r in rows
    ]
