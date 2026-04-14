from datetime import datetime

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
