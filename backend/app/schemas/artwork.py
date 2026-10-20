import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.schemas.artist import ArtistOut
from app.schemas.technique import TechniqueOut
from app.schemas.room import RoomOut
from app.schemas.storage import StorageOptionOut


class ImageOut(BaseModel):
    id: int
    url: str
    is_primary: bool
    is_internal: bool = False
    sort_order: int

    model_config = {"from_attributes": True}


_YEAR_RE = re.compile(r"(?<!\d)(1\d{3}|20\d{2})(?!\d)")


def split_year(text: str | None) -> tuple[int | None, str | None]:
    """Свободный ввод года → (год для фильтров/сортировки, текст для показа).

    "1967" → (1967, None); "2016-2017" → (2016, "2016-2017"); "2000-е" → (2000, "2000-е");
    "конец XIX в." → (None, "конец XIX в."). Чистое число в тексте не храним.
    """
    text = " ".join((text or "").split())
    if not text:
        return None, None
    if text.isdigit():
        return int(text), None
    m = _YEAR_RE.search(text)
    return (int(m.group(1)) if m else None), text[:50]


class _YearTextMixin(BaseModel):
    year_text: str | None = None

    @model_validator(mode="after")
    def _apply_year_text(self):
        # year_text приоритетнее year: из него же выводим числовой год
        if "year_text" in self.model_fields_set:
            self.year, self.year_text = split_year(self.year_text)
        elif "year" in self.model_fields_set:
            self.year_text = None  # пришёл только числовой год — старый текст устарел
        return self


class ArtworkCreate(_YearTextMixin):
    title: str | None = None
    artist_id: int
    year: int | None = None
    edition: str | None = None
    description: str | None = None
    condition: str | None = None
    provenance: str | None = None
    style_period: str | None = None
    has_expertise: bool = False
    status: str = "draft"
    warehouse_id: int | None = None
    rack_id: int | None = None
    shelf_id: int | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    currency: str | None = None  # None → берём дефолтную из настроек
    notes: str | None = None
    room_id: int | None = None
    is_framed: bool = False
    tags: list[str] = []
    technique_ids: list[int] = []


class ArtworkUpdate(_YearTextMixin):
    title: str | None = None
    artist_id: int | None = None
    year: int | None = None
    edition: str | None = None
    description: str | None = None
    condition: str | None = None
    provenance: str | None = None
    style_period: str | None = None
    has_expertise: bool | None = None
    status: str | None = None
    warehouse_id: int | None = None
    rack_id: int | None = None
    shelf_id: int | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    room_id: int | None = None
    is_framed: bool | None = None
    tags: list[str] | None = None
    technique_ids: list[int] | None = None
    reserved_client_id: int | None = None
    reserved_until: date | None = None
    reserve_note: str | None = None
    exhibition_from: date | None = None
    exhibition_to: date | None = None
    exhibition_place: str | None = None


class ArtworkOut(BaseModel):
    id: int
    inventory_number: int
    title: str | None
    artist: ArtistOut
    year: int | None
    year_text: str | None = None
    edition: str | None
    description: str | None
    condition: str | None
    provenance: str | None = None
    style_period: str | None = None
    has_expertise: bool
    status: str
    warehouse: StorageOptionOut | None = None
    rack: StorageOptionOut | None = None
    shelf: StorageOptionOut | None = None
    width_cm: float | None
    height_cm: float | None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None
    currency: str = "USD"
    notes: str | None
    room: RoomOut | None = None
    is_framed: bool
    tags: list[str]
    reserved_client_id: int | None = None
    reserved_until: date | None = None
    reserve_note: str | None = None
    exhibition_from: date | None = None
    exhibition_to: date | None = None
    exhibition_place: str | None = None
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
    currency: str = "USD"
    primary_image: str | None = None
    year: int | None
    year_text: str | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    room: RoomOut | None = None
    is_framed: bool = False
    tags: list[str] = []
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}
