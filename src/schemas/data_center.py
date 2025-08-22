from pydantic import BaseModel


class ItemTypeSchemas(BaseModel):
    id: int
    name: str


class ItemSchemas(BaseModel):
    id: int
    name: str
