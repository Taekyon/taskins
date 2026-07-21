from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class GroupOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
