from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from D3Database.enums.category_item_enum import CategoryEnum
from src.controllers.item_price_history import ItemPriceHistoryController
from src.database import session_local
from src.models.item_price_history import QuantityEnum
from src.schemas.item_price_history import (
    CreateItemPriceHistorySchema,
    PriceResellEvaluationSchema,
    ProfitableCraftSchema,
    ProfitableItemSchema,
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


@router.get("/evaluate_resell", response_model=PriceResellEvaluationSchema)
def evaluate_resell(
    gid: int,
    observed_price: float,
    server_id: int,
    quantity: QuantityEnum | None = None,
    lookback_days: int = 30,
    session: Session = Depends(session_local),
):
    """Endpoint pour évaluer si l'achat/revente est potentiellement rentable.

    Paramètres :
    - gid : ID de l'item à évaluer
    - observed_price : Prix observé pour cet item
    - server_id : ID du serveur
    - quantity : Quantité spécifique à évaluer (None = toutes les quantités)
    - lookback_days : Nombre de jours d'historique à analyser
    """
    return ItemPriceHistoryController.is_price_resell_profitable(
        session, gid, quantity, server_id, observed_price, lookback_days
    )


@router.get("/top_profitable_items", response_model=list[ProfitableItemSchema])
def get_top_profitable_items(
    server_id: int,
    quantity: QuantityEnum | None = None,
    lookback_days: int = 30,
    min_samples: int = 5,
    top_n: int = 50,
    category: CategoryEnum | None = None,
    type_id: int | None = None,
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

    Paramètres de filtrage :
    - quantity : Quantité spécifique à filtrer (None = toutes les quantités)
    - category : Catégorie d'items (EQUIPMENT, CONSUMABLES, RESOURCES, QUEST, OTHER, COSMETICS)
    - type_id : ID du type d'item spécifique
    """
    return ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days, min_samples, top_n, category, type_id
    )


@router.get("/top_profitable_crafts", response_model=list[ProfitableCraftSchema])
def get_top_profitable_crafts(
    server_id: int,
    quantity: QuantityEnum | None = None,
    lookback_days: int = 30,
    min_samples: int = 5,
    top_n: int = 50,
    category: CategoryEnum | None = None,
    type_id: int | None = None,
    session: Session = Depends(session_local),
):
    """Retourne un classement des items les plus rentables à crafter.

    Pour chaque recette disponible :
    - Calcule le coût total des ingrédients (basé sur les prix moyens)
    - Calcule le prix de vente moyen de l'item crafté
    - Vérifie que l'item crafté se vend (a un historique de prix)
    - Calcule le profit potentiel (prix de vente - coût de craft)
    - Calcule la marge de profit en pourcentage

    Les items sont triés par profit potentiel décroissant.

    Paramètres de filtrage :
    - quantity : Quantité spécifique à filtrer (None = toutes les quantités)
    - category : Catégorie d'items à crafter (EQUIPMENT, CONSUMABLES, RESOURCES, QUEST, OTHER, COSMETICS)
    - type_id : ID du type d'item à crafter
    """
    return ItemPriceHistoryController.get_top_profitable_crafts(
        session, server_id, quantity, lookback_days, min_samples, top_n, category, type_id
    )
