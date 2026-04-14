from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import get_current_user
from app.models import Client, Artist, User
from app.schemas.client import ClientCreate, ClientUpdate, ClientOut

router = APIRouter()


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


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Client).options(selectinload(Client.preferred_artists)).where(Client.id == client_id)
    client = (await db.execute(stmt)).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientOut)
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
