from pydantic import BaseModel


class TechniqueOut(BaseModel):
    id: int
    name: str
    category: str | None

    model_config = {"from_attributes": True}
