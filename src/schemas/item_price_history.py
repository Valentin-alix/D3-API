from datetime import datetime

from pydantic import BaseModel

from src.models.item_price_history import QuantityEnum


class CreateItemPriceHistorySchema(BaseModel):
    gid: int
    quantity: QuantityEnum
    price: int
    recorded_at: datetime
    server_id: int
