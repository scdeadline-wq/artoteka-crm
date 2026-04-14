from pydantic import BaseModel


class ArtistCreate(BaseModel):
    name_ru: str
    name_en: str | None = None
    is_group: bool = False
    bio: str | None = None


class ArtistUpdate(BaseModel):
    name_ru: str | None = None
    name_en: str | None = None
    is_group: bool | None = None
    bio: str | None = None


class ArtistOut(BaseModel):
    id: int
    name_ru: str
    name_en: str | None
    is_group: bool
    bio: str | None

    model_config = {"from_attributes": True}
