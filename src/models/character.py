from enum import StrEnum, auto
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum
from src.models.base import Base


class CharacterActionEnum(StrEnum):
    MULE_ACCEPT_BANK = auto()


class Character(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(unique=True)
    server_id: Mapped[int]
    action: Mapped[CharacterActionEnum | None] = mapped_column(
        SQLEnum(CharacterActionEnum)
    )
