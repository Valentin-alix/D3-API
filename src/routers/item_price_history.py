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


@router.post("/get_sales_speed", response_model=dict[int, float])
def get_sales_speed_by_gid(
    server_id: int,
    gids: list[int],
    quantity: QuantityEnum = QuantityEnum.HUNDRED,
    session: Session = Depends(session_local),
):
    return ItemPriceHistoryController.get_sales_speed_from_prices(
        session, quantity, server_id, gids
    )


@router.get("/evolution_price", response_model=list[ReadItemPriceHistorySchema])
def get_evolution_price(
    server_id: int,
    type_id: int,
    item_gid: int | None = None,
    quantity: QuantityEnum = QuantityEnum.HUNDRED,
    session: Session = Depends(session_local),
):
    return ItemPriceHistoryController.get_evolution_price(
        session, quantity, server_id, type_id, item_gid
    )


@router.get("/evaluate_resell")
def evaluate_resell(
    gid: int,
    observed_price: float,
    server_id: int,
    quantity: QuantityEnum = QuantityEnum.HUNDRED,
    lookback_days: int = 30,
    session: Session = Depends(session_local),
):
    """Endpoint pour évaluer si l'achat/revente est potentiellement rentable."""
    return ItemPriceHistoryController.is_price_resell_profitable(
        session, gid, quantity, server_id, observed_price, lookback_days
    )


@router.get("/top_profitable_items")
def get_top_profitable_items(
    server_id: int,
    quantity: QuantityEnum = QuantityEnum.HUNDRED,
    lookback_days: int = 30,
    min_samples: int = 5,
    top_n: int = 50,
    session: Session = Depends(session_local),
):
    """Retourne un classement des items les plus rentables à acheter pour revendre.

    Calcule pour chaque item :
    - Prix moyen, minimum et maximum
    - Potentiel de profit (différence entre prix moyen et minimum)
    - Marge de profit en pourcentage
    - Score de rentabilité (combinaison du potentiel et de la marge)
    - Volatilité des prix

    Les items sont triés par score de rentabilité décroissant.
    """
    return ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days, min_samples, top_n
    )
