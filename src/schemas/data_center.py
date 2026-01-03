from pydantic import BaseModel


class ItemTypeOptionSchema(BaseModel):
    id: int
    name: str


class ItemOptionSchema(BaseModel):
    id: int
    name: str
