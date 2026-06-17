from pydantic import BaseModel


class StorageOptionOut(BaseModel):
    id: int
    kind: str
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class StorageOptionCreate(BaseModel):
    kind: str
    name: str
    sort_order: int = 0


class StorageOptionUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
