from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.models import Sale, Artwork, ArtworkStatus, Client, User
from app.schemas.sale import SaleCreate, SaleOut

router = APIRouter()


@router.get("/", response_model=list[SaleOut])
async def list_sales(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Sale)
        .options(
            selectinload(Sale.artwork).selectinload(Artwork.artist),
            selectinload(Sale.client),
            selectinload(Sale.referral),
        )
        .order_by(Sale.sold_at.desc())
    )
    sales = (await db.execute(stmt)).scalars().all()
    return [_sale_to_out(s) for s in sales]


@router.post("/", response_model=SaleOut, status_code=201)
async def create_sale(
    body: SaleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
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
    )
    sale = (await db.execute(stmt)).scalar_one()
    return _sale_to_out(sale)


def _sale_to_out(sale: Sale) -> SaleOut:
    margin = None
    if sale.artwork.purchase_price is not None:
        margin = sale.sold_price - sale.artwork.purchase_price
        if sale.referral_fee:
            margin -= sale.referral_fee

    return SaleOut(
        id=sale.id,
        artwork_id=sale.artwork_id,
        artwork_title=sale.artwork.title,
        artist_name=sale.artwork.artist.name_ru if sale.artwork.artist else None,
        client_id=sale.client_id,
        client_name=sale.client.name,
        referral_id=sale.referral_id,
        referral_name=sale.referral.name if sale.referral else None,
        sold_price=sale.sold_price,
        purchase_price=sale.artwork.purchase_price,
        referral_fee=sale.referral_fee,
        margin=margin,
        notes=sale.notes,
        sold_at=sale.sold_at,
    )
