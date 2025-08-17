from datetime import datetime
from enum import IntEnum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from D3Database.data_center.data_reader import DataReader
from D3Database.data_center.i18n import I18N
from src.models.base import Base


class QuantityEnum(IntEnum):
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

    @hybrid_property
    def name(self) -> str:
        name_id = DataReader().item_by_id[self.gid].nameId
        if not name_id:
            return ""
        return I18N().name_by_id[name_id]
