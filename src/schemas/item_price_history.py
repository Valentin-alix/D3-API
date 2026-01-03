from datetime import datetime

from pydantic import BaseModel, PositiveInt

from src.models.item_price_history import QuantityEnum


class CreateItemPriceHistorySchema(BaseModel):
    gid: int
    quantity: QuantityEnum
    price: PositiveInt | None
    server_id: int


class ReadItemPriceHistorySchema(BaseModel):
    name: str
    quantity: QuantityEnum
    price: PositiveInt | None
    recorded_at: datetime


class PriceResellEvaluationSchema(BaseModel):
    """Schéma pour l'évaluation de la rentabilité d'un achat/revente."""

    is_low: bool
    avg_price: float | None
    median_price: float | None
    samples: int
    fraction_higher: float
    recommended_action: str  # 'buy' | 'consider' | 'avoid'
    reason: str


class ProfitableItemSchema(BaseModel):
    """Schéma pour un item rentable à acheter/revendre."""

    gid: int
    name: str
    avg_price: float
    min_price: float
    max_price: float
    profit_potential: float
    profit_margin_pct: float
    profitability_score: float
    volatility: float
    samples: int


class IngredientDetailSchema(BaseModel):
    """Schéma pour les détails d'un ingrédient de craft."""

    id: int
    name: str
    quantity: int
    unit_price: float
    total_price: float


class ProfitableCraftSchema(BaseModel):
    """Schéma pour un craft rentable."""

    result_id: int
    result_name: str
    sell_price: float
    craft_cost: float
    profit: float
    profit_margin_pct: float
    ingredients: list[IngredientDetailSchema]
    samples: int
