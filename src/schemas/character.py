from pydantic import BaseModel


class CharacterCreateSchema(BaseModel):
    id: int
    server_id: int
