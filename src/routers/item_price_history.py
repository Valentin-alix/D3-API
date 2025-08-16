from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.item_price_history import ItemPriceHistoryController
from src.database import session_local
from src.models.item_price_history import QuantityEnum
from src.schemas.item_price_history import (
    CreateItemPriceHistorySchema,
    ReadItemPriceHistorySchema,
)

router = APIRouter(prefix="/item_price_history")


@router.post("/bulk_insert", status_code=status.HTTP_201_CREATED)
def bulk_insert_item_price_history(
    payloads: list[CreateItemPriceHistorySchema],
    session: Session = Depends(session_local),
):
    if len(payloads) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uncorrect amount of price history",
        )
    ItemPriceHistoryController.bulk_insert(session, payloads)


@router.get("/sales_speed", response_model=dict[int, float])
def get_sales_speed_by_gid(
    server_id: int,
    quantity: QuantityEnum = QuantityEnum.HUNDRED,
    session: Session = Depends(session_local),
):
    return ItemPriceHistoryController.get_sales_speed_from_prices(
        session, quantity, server_id
    )


@router.get("/evolution_price", response_model=list[ReadItemPriceHistorySchema])
def get_evolution_price(
    server_id: int,
    quantity: QuantityEnum = QuantityEnum.HUNDRED,
    session: Session = Depends(session_local),
):
    return ItemPriceHistoryController.get_evolution_price(session, quantity, server_id)
