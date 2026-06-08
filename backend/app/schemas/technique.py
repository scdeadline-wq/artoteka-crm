from pydantic import BaseModel


class TechniqueCreate(BaseModel):
    name: str
    category: str | None = None


class TechniqueOut(BaseModel):
    id: int
    name: str
    category: str | None

    model_config = {"from_attributes": True}
