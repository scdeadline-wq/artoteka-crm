from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.artist import ArtistOut


class ClientCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    telegram: str | None = None
    client_type: str = "buyer"
    description: str | None = None
    preferred_artist_ids: list[int] = []


class ClientUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    telegram: str | None = None
    client_type: str | None = None
    description: str | None = None
    preferred_artist_ids: list[int] | None = None


class ClientOut(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    telegram: str | None
    client_type: str
    description: str | None
    preferred_artists: list[ArtistOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientPurchase(BaseModel):
    """Покупка клиента для карточки (без закупочных цен/маржи)."""
    id: int
    artwork_id: int
    artwork_title: str | None
    artist_name: str | None
    sold_price: Decimal
    currency: str = "USD"
    sold_at: datetime


class ClientDetailOut(ClientOut):
    purchases: list[ClientPurchase] = []


class SelectionItem(BaseModel):
    """Работа в подборке клиента."""
    artwork_id: int
    inventory_number: int
    artwork_title: str | None = None
    artist_name: str | None = None
    primary_image: str | None = None
    status: str  # shortlist | sent
    note: str | None = None
    sale_price: Decimal | None = None
    currency: str = "USD"
    artwork_status: str  # текущий статус работы (for_sale/sold/...)


class SelectionCreate(BaseModel):
    artwork_id: int
    status: str = "shortlist"
    note: str | None = None


class SelectionUpdate(BaseModel):
    status: str | None = None
    note: str | None = None
