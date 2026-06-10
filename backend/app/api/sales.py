import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user, is_admin
from app.models import Sale, Artwork, ArtworkStatus, Client, User
from app.schemas.sale import SaleCreate, SaleOut

router = APIRouter()


def _sales_stmt(date_from: date | None = None, date_to: date | None = None):
    """Базовый запрос продаж. include_deleted — чтобы продажи по мягко
    удалённым работам не теряли artwork (иначе 500 в сериализации)."""
    stmt = (
        select(Sale)
        .options(
            selectinload(Sale.artwork).selectinload(Artwork.artist),
            selectinload(Sale.client),
            selectinload(Sale.referral),
        )
        .order_by(Sale.sold_at.desc())
        .execution_options(include_deleted=True)
    )
    if date_from:
        stmt = stmt.where(func.date(Sale.sold_at) >= date_from)
    if date_to:
        stmt = stmt.where(func.date(Sale.sold_at) <= date_to)
    return stmt


@router.get("/", response_model=list[SaleOut])
async def list_sales(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sales = (await db.execute(_sales_stmt(date_from, date_to))).scalars().all()
    return [_sale_to_out(s, user) for s in sales]


@router.get("/export/")
async def export_sales(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Экспорт продаж в CSV (UTF-8 BOM для Excel). Закупочная цена и маржа —
    только для admin/owner (как и в JSON-выдаче)."""
    sales = (await db.execute(_sales_stmt(date_from, date_to))).scalars().all()
    admin = is_admin(user)

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    header = ["Дата", "Инв. номер", "Название", "Художник", "Клиент", "Цена продажи"]
    if admin:
        header += ["Закупочная цена", "Маржа"]
    writer.writerow(header)

    for sale in sales:
        artwork = sale.artwork
        row = [
            sale.sold_at.strftime("%d.%m.%Y") if sale.sold_at else "",
            artwork.inventory_number if artwork else "",
            (artwork.title or "") if artwork else "",
            (artwork.artist.name_ru if artwork.artist else "") if artwork else "",
            sale.client.name if sale.client else "",
            sale.sold_price,
        ]
        if admin:
            purchase = artwork.purchase_price if artwork else None
            margin = ""
            if purchase is not None:
                margin = sale.sold_price - purchase
                if sale.referral_fee:
                    margin -= sale.referral_fee
            row += [purchase if purchase is not None else "", margin]
        writer.writerow(row)

    # utf-8-sig добавляет BOM — чтобы Excel корректно открывал кириллицу
    csv_bytes = buf.getvalue().encode("utf-8-sig")
    return FastAPIResponse(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sales.csv"'},
    )


@router.post("/", response_model=SaleOut, status_code=201)
async def create_sale(
    body: SaleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    artwork = await db.get(Artwork, body.artwork_id)
    if not artwork:
        raise HTTPException(status_code=400, detail="Artwork not found")
    if artwork.status == ArtworkStatus.sold:
        raise HTTPException(status_code=400, detail="Artwork already sold")

    client = await db.get(Client, body.client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Client not found")

    sale = Sale(**body.model_dump())
    artwork.status = ArtworkStatus.sold
    db.add(sale)
    await db.commit()

    # Reload
    stmt = (
        select(Sale)
        .options(
            selectinload(Sale.artwork).selectinload(Artwork.artist),
            selectinload(Sale.client),
            selectinload(Sale.referral),
        )
        .where(Sale.id == sale.id)
        .execution_options(include_deleted=True)
    )
    sale = (await db.execute(stmt)).scalar_one()
    return _sale_to_out(sale, user)


@router.delete("/{sale_id}/", status_code=204)
async def cancel_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Отмена продажи: запись удаляется, работа возвращается в статус for_sale."""
    sale = await db.get(Sale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # Работа может быть мягко удалена — ищем с обходом фильтра
    stmt = (
        select(Artwork)
        .where(Artwork.id == sale.artwork_id)
        .execution_options(include_deleted=True)
    )
    artwork = (await db.execute(stmt)).scalar_one_or_none()
    if artwork:
        artwork.status = ArtworkStatus.for_sale

    await db.delete(sale)
    await db.commit()
    return FastAPIResponse(status_code=204)


def _sale_to_out(sale: Sale, user: User) -> SaleOut:
    admin = is_admin(user)
    artwork = sale.artwork  # может отсутствовать (защита от рассинхрона)
    purchase_price = artwork.purchase_price if (admin and artwork) else None

    margin = None
    if admin and artwork and artwork.purchase_price is not None:
        margin = sale.sold_price - artwork.purchase_price
        if sale.referral_fee:
            margin -= sale.referral_fee

    return SaleOut(
        id=sale.id,
        artwork_id=sale.artwork_id,
        artwork_title=artwork.title if artwork else None,
        artist_name=artwork.artist.name_ru if (artwork and artwork.artist) else None,
        client_id=sale.client_id,
        client_name=sale.client.name,
        referral_id=sale.referral_id,
        referral_name=sale.referral.name if sale.referral else None,
        sold_price=sale.sold_price,
        purchase_price=purchase_price,
        referral_fee=sale.referral_fee,
        margin=margin,
        notes=sale.notes,
        sold_at=sale.sold_at,
    )
