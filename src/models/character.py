from enum import Enum
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum
from src.models.base import Base


class CharacterActionEnum(Enum):
    MULE_ACCEPT_BANK = "mule_accept_bank"


class Character(Base):
    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=False)
    server_id: Mapped[int]
    action: Mapped[CharacterActionEnum | None] = mapped_column(
        SQLEnum(CharacterActionEnum, name="character_action"), default=None
    )
