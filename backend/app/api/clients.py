from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.models import Client, Artist, User, Sale, Artwork
from app.models.selection import ClientSelection, SELECTION_STATUSES
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientOut, ClientDetailOut, ClientPurchase,
    SelectionItem, SelectionCreate, SelectionUpdate,
)

router = APIRouter()


def _primary_image(artwork: Artwork) -> str | None:
    imgs = sorted(artwork.images or [], key=lambda i: (not i.is_primary, i.sort_order))
    return imgs[0].url if imgs else None


def _selection_to_item(sel: ClientSelection) -> SelectionItem:
    a = sel.artwork
    return SelectionItem(
        artwork_id=sel.artwork_id,
        inventory_number=a.inventory_number,
        artwork_title=a.title,
        artist_name=a.artist.name_ru if a.artist else None,
        primary_image=_primary_image(a),
        status=sel.status,
        note=sel.note,
        sale_price=a.sale_price,
        currency=a.currency or "USD",
        artwork_status=a.status.value if hasattr(a.status, "value") else str(a.status),
    )


@router.get("/", response_model=list[ClientOut])
async def list_clients(
    q: str | None = None,
    client_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Client).options(selectinload(Client.preferred_artists)).order_by(Client.name)
    if q:
        stmt = stmt.where(Client.name.ilike(f"%{q}%"))
    if client_type:
        stmt = stmt.where(Client.client_type == client_type)
    return (await db.execute(stmt)).scalars().all()


@router.post("/", response_model=ClientOut, status_code=201)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = body.model_dump(exclude={"preferred_artist_ids"})
    client = Client(**data)

    if body.preferred_artist_ids:
        artists = (await db.execute(
            select(Artist).where(Artist.id.in_(body.preferred_artist_ids))
        )).scalars().all()
        client.preferred_artists = list(artists)

    db.add(client)
    await db.commit()

    stmt = select(Client).options(selectinload(Client.preferred_artists)).where(Client.id == client.id)
    return (await db.execute(stmt)).scalar_one()


@router.get("/{client_id}/", response_model=ClientDetailOut)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Client)
        .options(
            selectinload(Client.preferred_artists),
            selectinload(Client.purchases)
            .selectinload(Sale.artwork)
            .selectinload(Artwork.artist),
        )
        .where(Client.id == client_id)
    )
    client = (await db.execute(stmt)).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    purchases = [
        ClientPurchase(
            id=s.id,
            artwork_id=s.artwork_id,
            artwork_title=s.artwork.title if s.artwork else None,
            artist_name=s.artwork.artist.name_ru if s.artwork and s.artwork.artist else None,
            sold_price=s.sold_price,
            currency=s.currency or "USD",
            sold_at=s.sold_at,
        )
        for s in sorted(client.purchases, key=lambda x: x.sold_at, reverse=True)
    ]
    # ВАЖНО: не через ClientDetailOut.model_validate(client) — он пытается
    # провалидировать client.purchases (ORM-объекты Sale) в ClientPurchase и падает
    # (500) у клиентов с покупками. Собираем базовые поля через ClientOut, purchases — отдельно.
    base = ClientOut.model_validate(client)
    return ClientDetailOut(**base.model_dump(), purchases=purchases)


@router.put("/{client_id}/", response_model=ClientOut)
async def update_client(
    client_id: int,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Client).options(selectinload(Client.preferred_artists)).where(Client.id == client_id)
    client = (await db.execute(stmt)).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    data = body.model_dump(exclude_unset=True)
    artist_ids = data.pop("preferred_artist_ids", None)

    for key, value in data.items():
        setattr(client, key, value)

    if artist_ids is not None:
        artists = (await db.execute(
            select(Artist).where(Artist.id.in_(artist_ids))
        )).scalars().all()
        client.preferred_artists = list(artists)

    await db.commit()
    await db.refresh(client)
    return client


@router.delete("/{client_id}/", status_code=200)
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Удалить клиента. Запрещаем, если за ним числятся покупки или он указан
    как реферал — иначе осиротеет история продаж."""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    sales_count = (await db.execute(
        select(func.count(Sale.id)).where(
            (Sale.client_id == client_id) | (Sale.referral_id == client_id)
        )
    )).scalar() or 0
    if sales_count:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя удалить: за клиентом числится продаж — {sales_count}. "
                   "История продаж должна сохраниться.",
        )

    await db.delete(client)
    await db.commit()
    return {"ok": True, "id": client_id}


# ── Подборка работ под клиента (shortlist / отправлено на просмотр) ───────────

def _check_selection_status(status: str) -> None:
    if status not in SELECTION_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Недопустимый статус «{status}». Допустимые: {', '.join(SELECTION_STATUSES)}",
        )


def _selection_query(client_id: int):
    return (
        select(ClientSelection)
        .options(
            selectinload(ClientSelection.artwork).selectinload(Artwork.artist),
            selectinload(ClientSelection.artwork).selectinload(Artwork.images),
        )
        .where(ClientSelection.client_id == client_id)
        .order_by(ClientSelection.created_at.desc())
    )


@router.get("/{client_id}/selection/", response_model=list[SelectionItem])
async def list_selection(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sels = (await db.execute(_selection_query(client_id))).scalars().all()
    # Работа могла быть удалена → soft-delete фильтр уберёт artwork; пропускаем такие
    return [_selection_to_item(s) for s in sels if s.artwork]


@router.post("/{client_id}/selection/", response_model=SelectionItem, status_code=201)
async def add_to_selection(
    client_id: int,
    body: SelectionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _check_selection_status(body.status)
    if not await db.get(Client, client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    if not await db.get(Artwork, body.artwork_id):
        raise HTTPException(status_code=400, detail="Artwork not found")

    existing = (await db.execute(
        select(ClientSelection).where(
            ClientSelection.client_id == client_id,
            ClientSelection.artwork_id == body.artwork_id,
        )
    )).scalar_one_or_none()
    if existing:
        existing.status = body.status
        if body.note is not None:
            existing.note = body.note
        sel_id = existing.id
    else:
        sel = ClientSelection(
            client_id=client_id, artwork_id=body.artwork_id,
            status=body.status, note=body.note,
        )
        db.add(sel)
        await db.flush()
        sel_id = sel.id
    await db.commit()

    sel = (await db.execute(
        _selection_query(client_id).where(ClientSelection.id == sel_id)
    )).scalar_one()
    return _selection_to_item(sel)


@router.patch("/{client_id}/selection/{artwork_id}/", response_model=SelectionItem)
async def update_selection(
    client_id: int,
    artwork_id: int,
    body: SelectionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sel = (await db.execute(
        select(ClientSelection).where(
            ClientSelection.client_id == client_id,
            ClientSelection.artwork_id == artwork_id,
        )
    )).scalar_one_or_none()
    if not sel:
        raise HTTPException(status_code=404, detail="Not in selection")
    data = body.model_dump(exclude_unset=True)
    if data.get("status") is not None:
        _check_selection_status(data["status"])
        sel.status = data["status"]
    if "note" in data:
        sel.note = data["note"]
    await db.commit()

    sel = (await db.execute(
        _selection_query(client_id).where(ClientSelection.id == sel.id)
    )).scalar_one()
    return _selection_to_item(sel)


@router.delete("/{client_id}/selection/{artwork_id}/", status_code=200)
async def remove_from_selection(
    client_id: int,
    artwork_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sel = (await db.execute(
        select(ClientSelection).where(
            ClientSelection.client_id == client_id,
            ClientSelection.artwork_id == artwork_id,
        )
    )).scalar_one_or_none()
    if sel:
        await db.delete(sel)
        await db.commit()
    return {"ok": True}
