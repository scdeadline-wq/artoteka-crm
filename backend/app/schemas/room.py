from datetime import datetime

from pydantic import BaseModel


class RoomOut(BaseModel):
    id: int
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class RoomDetailOut(RoomOut):
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    name: str
    sort_order: int = 0


class RoomUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
