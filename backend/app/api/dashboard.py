from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user, is_admin
from app.currency import normalize_currency
from app.models import Sale, Artwork, ArtworkStatus, Artist, User
from app.schemas.sale import SaleOut
from app.services.settings import get_default_currency

router = APIRouter()


def _by_currency(rows) -> dict[str, float]:
    """[(currency, sum)] → {code: float}, нормализуя код валюты."""
    out: dict[str, float] = {}
    for code, total in rows:
        c = normalize_currency(code)
        out[c] = out.get(c, 0.0) + float(total or 0)
    return out


@router.get("/summary/")
async def summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Выручка и кол-во продаж — с разбивкой по валютам (без конвертации)
    rev_rows = (await db.execute(
        select(Sale.currency, func.coalesce(func.sum(Sale.sold_price), 0)).group_by(Sale.currency)
    )).all()
    revenue_by_currency = _by_currency(rev_rows)
    total_sales = (await db.execute(select(func.count(Sale.id)))).scalar() or 0

    # Реферальные выплаты по валютам
    ref_rows = (await db.execute(
        select(Sale.currency, func.coalesce(func.sum(Sale.referral_fee), 0)).group_by(Sale.currency)
    )).all()
    referral_by_currency = _by_currency(ref_rows)

    # Работы по статусам
    status_result = await db.execute(
        select(Artwork.status, func.count(Artwork.id)).group_by(Artwork.status)
    )
    statuses = {row[0].value: row[1] for row in status_result.all()}

    result = {
        "total_sales": total_sales,
        "revenue_by_currency": revenue_by_currency,
        "referral_by_currency": referral_by_currency,
        "artworks_by_status": statuses,
        "default_currency": await get_default_currency(db),
    }

    # Закупка и маржа — только для admin, тоже по валютам
    if is_admin(user):
        pur_rows = (await db.execute(
            select(Artwork.currency, func.coalesce(func.sum(Artwork.purchase_price), 0))
            .where(Artwork.status == ArtworkStatus.sold)
            .group_by(Artwork.currency)
        )).all()
        purchase_by_currency = _by_currency(pur_rows)
        codes = set(revenue_by_currency) | set(referral_by_currency) | set(purchase_by_currency)
        margin_by_currency = {
            c: revenue_by_currency.get(c, 0.0)
            - referral_by_currency.get(c, 0.0)
            - purchase_by_currency.get(c, 0.0)
            for c in codes
        }
        result["purchase_by_currency"] = purchase_by_currency
        result["margin_by_currency"] = margin_by_currency

    return result


@router.get("/recent-sales/", response_model=list[SaleOut])
async def recent_sales(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Последние сделки для дашборда."""
    from app.api.sales import _sale_to_out

    stmt = (
        select(Sale)
        .options(
            selectinload(Sale.artwork).selectinload(Artwork.artist),
            selectinload(Sale.client),
            selectinload(Sale.referral),
        )
        .order_by(Sale.sold_at.desc())
        .limit(limit)
        .execution_options(include_deleted=True)
    )
    sales = (await db.execute(stmt)).scalars().all()
    return [_sale_to_out(s, user) for s in sales]


@router.get("/top-artists/")
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
            Sale.currency,
        )
        .join(Artwork, Artwork.artist_id == Artist.id)
        .join(Sale, Sale.artwork_id == Artwork.id)
        .group_by(Artist.id, Sale.currency)
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
            "currency": normalize_currency(r[4]),
        }
        for r in rows
    ]
