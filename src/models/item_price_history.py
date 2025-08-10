from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class QuantityEnum(Enum):
    ONE = 1
    TEN = 10
    HUNDRED = 100
    THOUSAND = 1000


QuantitySQLEnum = SQLEnum(QuantityEnum)


class ItemPriceHistory(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    gid: Mapped[int]
    quantity: Mapped[QuantityEnum] = mapped_column(QuantitySQLEnum)
    price: Mapped[int | None]
    recorded_at: Mapped[datetime]
    server_id: Mapped[int]
