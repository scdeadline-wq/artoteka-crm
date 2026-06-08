from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.artist import ArtistOut
from app.schemas.technique import TechniqueOut
from app.schemas.room import RoomOut


class ImageOut(BaseModel):
    id: int
    url: str
    is_primary: bool
    sort_order: int

    model_config = {"from_attributes": True}


class ArtworkCreate(BaseModel):
    title: str | None = None
    artist_id: int
    year: int | None = None
    edition: str | None = None
    description: str | None = None
    condition: str | None = None
    style_period: str | None = None
    has_expertise: bool = False
    status: str = "draft"
    location: str | None = None
    rack: str | None = None
    shelf: str | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    notes: str | None = None
    room_id: int | None = None
    is_framed: bool = False
    tags: list[str] = []
    technique_ids: list[int] = []


class ArtworkUpdate(BaseModel):
    title: str | None = None
    artist_id: int | None = None
    year: int | None = None
    edition: str | None = None
    description: str | None = None
    condition: str | None = None
    style_period: str | None = None
    has_expertise: bool | None = None
    status: str | None = None
    location: str | None = None
    rack: str | None = None
    shelf: str | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    notes: str | None = None
    room_id: int | None = None
    is_framed: bool | None = None
    tags: list[str] | None = None
    technique_ids: list[int] | None = None


class ArtworkOut(BaseModel):
    id: int
    inventory_number: int
    title: str | None
    artist: ArtistOut
    year: int | None
    edition: str | None
    description: str | None
    condition: str | None
    style_period: str | None = None
    has_expertise: bool
    status: str
    location: str | None
    rack: str | None = None
    shelf: str | None = None
    width_cm: float | None
    height_cm: float | None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None
    notes: str | None
    room: RoomOut | None = None
    is_framed: bool
    tags: list[str]
    deleted_at: datetime | None = None
    techniques: list[TechniqueOut]
    images: list[ImageOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArtworkListOut(BaseModel):
    id: int
    inventory_number: int
    title: str | None
    artist: ArtistOut
    status: str
    sale_price: Decimal | None
    primary_image: str | None = None
    year: int | None
    width_cm: float | None = None
    height_cm: float | None = None
    room: RoomOut | None = None
    is_framed: bool = False
    tags: list[str] = []
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}
