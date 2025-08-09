from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.controllers.item_price_history import ItemPriceHistoryController
from src.database import session_local
from src.schemas.item_price_history import CreateItemPriceHistorySchema

router = APIRouter(prefix="/item_price_history")


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_item_price_history(
    payload: CreateItemPriceHistorySchema, session: Session = Depends(session_local)
):
    ItemPriceHistoryController.create(session, payload)
