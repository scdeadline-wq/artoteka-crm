from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ShareLinkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    artist_ids: list[int] = []
    tags: list[str] = []
    only_available: bool = False
    show_prices: bool = True


class ShareLinkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    show_prices: bool | None = None
    is_active: bool | None = None


class ShareLinkOut(BaseModel):
    id: int
    token: str
    title: str
    artist_ids: list[int]
    tags: list[str]
    only_available: bool
    show_prices: bool
    is_active: bool
    created_at: datetime
    artworks_count: int = 0

    model_config = {"from_attributes": True}


class PublicArtwork(BaseModel):
    """Работа на публичной странице — без закупки, хранения, заметок и инв. номера."""
    id: int
    title: str | None
    artist_name: str | None
    year: str | None
    height_cm: float | None
    width_cm: float | None
    techniques: list[str]
    is_framed: bool
    description: str | None
    images: list[str]
    is_reserved: bool
    sale_price: Decimal | None = None
    currency: str | None = None


class PublicShareOut(BaseModel):
    title: str
    show_prices: bool
    artworks: list[PublicArtwork]
