from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SaleCreate(BaseModel):
    artwork_id: int
    client_id: int
    referral_id: int | None = None
    sold_price: Decimal
    referral_fee: Decimal | None = None
    currency: str | None = None  # None → берём дефолтную из настроек
    notes: str | None = None


class SaleOut(BaseModel):
    id: int
    artwork_id: int
    artwork_title: str | None = None
    artist_name: str | None = None
    client_id: int
    client_name: str
    referral_id: int | None
    referral_name: str | None = None
    sold_price: Decimal
    purchase_price: Decimal | None = None
    referral_fee: Decimal | None
    margin: Decimal | None = None
    currency: str = "USD"
    notes: str | None
    sold_at: datetime

    model_config = {"from_attributes": True}
