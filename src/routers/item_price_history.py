from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.controllers.item_price_history import ItemPriceHistoryController
from src.database import session_local
from src.schemas.item_price_history import CreateItemPriceHistorySchema

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
