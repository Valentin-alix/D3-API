from pydantic import BaseModel, PositiveInt

from src.models.item_price_history import QuantityEnum


class CreateItemPriceHistorySchema(BaseModel):
    gid: int
    quantity: QuantityEnum
    price: PositiveInt | None
    server_id: int
