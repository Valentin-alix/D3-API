import random
from datetime import datetime, timedelta

from sqlalchemy import Float, case, func, select
from sqlalchemy.orm import Session

from D3Database.data_center.data_reader import DataReader
from D3Database.data_center.i18n import I18N
from D3Database.enums.category_item_enum import CategoryEnum
from src.models.item_price_history import ItemPriceHistory, QuantityEnum
from src.schemas.item_price_history import (
    CreateItemPriceHistorySchema,
    IngredientDetailSchema,
    PriceResellEvaluationSchema,
    ProfitableCraftSchema,
    ProfitableItemSchema,
)


class ItemPriceHistoryController:
    @staticmethod
    def bulk_insert(session: Session, payloads: list[CreateItemPriceHistorySchema]):
        items_prices_histories = [
            ItemPriceHistory(
                gid=payload.gid,
                quantity=payload.quantity,
                price=payload.price,
                recorded_at=datetime.now(),
                server_id=payload.server_id,
            )
            for payload in payloads
        ]
        session.bulk_save_objects(items_prices_histories)
        session.commit()

    @staticmethod
    def get_sales_speed_from_prices(
        session: Session, quantity: QuantityEnum, server_id: int, gids: list[int]
    ):
        """
        Calculate sales speed based on price history.
        """
        increase_flag = case(
            (
                ItemPriceHistory.price
                > func.lag(ItemPriceHistory.price).over(
                    partition_by=ItemPriceHistory.gid,
                    order_by=ItemPriceHistory.recorded_at,
                ),
                1,
            ),
            else_=0,
        )

        subq = (
            session.query(
                ItemPriceHistory.gid.label("gid"),
                increase_flag.label("increase_flag"),
            )
            .filter(
                ItemPriceHistory.gid.in_(gids),
                ItemPriceHistory.quantity == quantity,
                ItemPriceHistory.server_id == server_id,
            )
            .subquery()
        )

        results = (
            session.query(
                subq.c.gid,
                (func.sum(subq.c.increase_flag).cast(Float) / func.count()).label(
                    "speed"
                ),
            )
            .group_by(subq.c.gid)
            .all()
        )

        return {gid: speed for gid, speed in results}

    @staticmethod
    def get_evolution_price(
        session: Session,
        quantity: QuantityEnum,
        server_id: int,
        type_id: int,
        item_gid: int | None = None,
    ):
        """Get the price evolution for a specific item type and quantity"""
        gids = (
            [
                item.id
                for item in DataReader().item_by_id.values()
                if item.typeId == type_id
            ]
            if item_gid is None
            else [item_gid]
        )
        return session.scalars(
            (
                select(ItemPriceHistory)
                .filter(
                    ItemPriceHistory.quantity == quantity,
                    ItemPriceHistory.server_id == server_id,
                    ItemPriceHistory.gid.in_(gids),
                )
                .order_by(ItemPriceHistory.recorded_at)
            )
        )

    @staticmethod
    def _generate_random_item_history(session: Session):
        """Just a helper function to generate random item price history, used for debug purpose"""
        items: list[ItemPriceHistory] = []
        for index in range(100):
            for gid in DataReader().item_by_id:
                items.append(
                    ItemPriceHistory(
                        gid=gid,
                        quantity=random.choice(list(QuantityEnum)),
                        price=gid + random.randint(0, 3),
                        recorded_at=datetime.now() + timedelta(seconds=index),
                        server_id=-1,
                    )
                )
        session.bulk_save_objects(items)
        session.commit()

    @staticmethod
    def is_price_resell_profitable(
        session: Session,
        gid: int,
        quantity: QuantityEnum | None,
        server_id: int,
        observed_price: float,
        lookback_days: int = 30,
        low_ratio: float = 0.6,
        min_samples: int = 5,
        fraction_higher_needed: float = 0.5,
    ) -> PriceResellEvaluationSchema:
        """Détermine si `observed_price` est suffisamment bas par rapport aux prix
        historiques pour envisager un achat/revente rentable.

        Retourne un schéma contenant des métriques et une recommandation.

        Si quantity est None, évalue sur toutes les quantités disponibles.
        """
        since = datetime.now() - timedelta(days=lookback_days)

        # Construire les filtres de base
        filters = [
            ItemPriceHistory.gid == gid,
            ItemPriceHistory.server_id == server_id,
            ItemPriceHistory.recorded_at >= since,
        ]

        # Ajouter le filtre de quantité si spécifié
        if quantity is not None:
            filters.append(ItemPriceHistory.quantity == quantity)

        prices_rows = (
            session.query(ItemPriceHistory.price)
            .filter(*filters)
            .order_by(ItemPriceHistory.recorded_at.desc())
            .all()
        )

        prices = [row[0] for row in prices_rows]
        samples = len(prices)

        if samples == 0:
            return PriceResellEvaluationSchema(
                is_low=False,
                avg_price=None,
                median_price=None,
                samples=0,
                fraction_higher=0.0,
                recommended_action="avoid",
                reason="no_data",
            )

        avg_price = sum(prices) / samples
        sorted_prices = sorted(prices)
        mid = samples // 2
        if samples % 2 == 1:
            median_price = sorted_prices[mid]
        else:
            median_price = (sorted_prices[mid - 1] + sorted_prices[mid]) / 2

        fraction_higher = sum(1 for price in prices if price > observed_price) / samples

        is_low_by_ratio = observed_price <= (avg_price * low_ratio)
        has_enough_samples = samples >= min_samples
        sells_higher_often = fraction_higher >= fraction_higher_needed

        is_low = is_low_by_ratio and has_enough_samples and sells_higher_often

        if not has_enough_samples:
            recommended_action = "consider"
            reason = "not_enough_samples"
        elif is_low:
            recommended_action = "buy"
            reason = "price_low_and_history_shows_higher_sales"
        else:
            recommended_action = "avoid"
            reason = "not_a_good_margin"

        return PriceResellEvaluationSchema(
            is_low=is_low,
            avg_price=avg_price,
            median_price=median_price,
            samples=samples,
            fraction_higher=fraction_higher,
            recommended_action=recommended_action,
            reason=reason,
        )

    @staticmethod
    def get_top_profitable_items(
        session: Session,
        server_id: int,
        quantity: QuantityEnum | None = None,
        lookback_days: int = 30,
        min_samples: int = 5,
        top_n: int = 50,
        category: CategoryEnum | None = None,
        type_id: int | None = None,
    ) -> list[ProfitableItemSchema]:
        """Retourne un classement des items les plus rentables à acheter pour revendre.

        Calcule pour chaque item ayant des données historiques :
        - Le prix moyen actuel (derniers enregistrements)
        - Le prix minimum observé
        - Le potentiel de profit (différence entre prix moyen et prix minimum)
        - La volatilité des prix (écart-type)

        Retourne une liste triée par rentabilité potentielle.

        Peut être filtré par catégorie, type d'item et quantité.
        """
        since = datetime.now() - timedelta(days=lookback_days)

        # Construire les filtres de base
        filters = [
            ItemPriceHistory.server_id == server_id,
            ItemPriceHistory.recorded_at >= since,
            ItemPriceHistory.price.isnot(None),
        ]

        # Ajouter le filtre de quantité si spécifié
        if quantity is not None:
            filters.append(ItemPriceHistory.quantity == quantity)

        # Récupérer les données de prix
        prices_data = (
            session.query(
                ItemPriceHistory.gid,
                ItemPriceHistory.price,
                ItemPriceHistory.recorded_at,
            )
            .filter(*filters)
            .order_by(ItemPriceHistory.gid, ItemPriceHistory.recorded_at)
            .all()
        )

        items_data = {}
        for gid, price, _ in prices_data:
            if gid not in items_data:
                items_data[gid] = []
            items_data[gid].append(price)

        # Filtrer par catégorie ou type d'item si spécifié
        data_reader = DataReader()
        if category is not None or type_id is not None:
            filtered_gids = set(items_data.keys())

            if category is not None:
                category_gids = data_reader.item_ids_by_category.get(category, set())
                filtered_gids &= category_gids

            if type_id is not None:
                type_gids = data_reader.item_ids_by_type_id.get(type_id, set())
                filtered_gids &= type_gids

            # Ne garder que les items filtrés
            items_data = {gid: prices for gid, prices in items_data.items() if gid in filtered_gids}

        profitable_items = []

        for gid, prices in items_data.items():
            if len(prices) < min_samples:
                continue

            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)

            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            std_dev = variance**0.5

            profit_potential = avg_price - min_price

            if min_price > 0:
                profit_margin_pct = (profit_potential / min_price) * 100
            else:
                profit_margin_pct = 0

            profitability_score = profit_potential * profit_margin_pct

            item_name = I18N().name_by_id[data_reader.item_by_id[gid].nameId]

            profitable_items.append(
                ProfitableItemSchema(
                    gid=gid,
                    name=item_name,
                    avg_price=round(avg_price, 2),
                    min_price=min_price,
                    max_price=max_price,
                    profit_potential=round(profit_potential, 2),
                    profit_margin_pct=round(profit_margin_pct, 2),
                    profitability_score=round(profitability_score, 2),
                    volatility=round(std_dev, 2),
                    samples=len(prices),
                )
            )

        profitable_items.sort(key=lambda x: x.profitability_score, reverse=True)

        return profitable_items[:top_n]

    @staticmethod
    def get_top_profitable_crafts(
        session: Session,
        server_id: int,
        quantity: QuantityEnum | None = None,
        lookback_days: int = 30,
        min_samples: int = 5,
        top_n: int = 50,
        category: CategoryEnum | None = None,
        type_id: int | None = None,
    ) -> list[ProfitableCraftSchema]:
        """Retourne un classement des items les plus rentables à crafter.

        Pour chaque recette disponible :
        - Calcule le coût total des ingrédients (basé sur les prix moyens)
        - Calcule le prix de vente moyen de l'item crafté
        - Vérifie que l'item crafté se vend (a un historique de prix)
        - Calcule le profit potentiel (prix de vente - coût de craft)
        - Calcule la marge de profit en pourcentage

        Retourne une liste triée par profit potentiel décroissant.

        Peut être filtré par catégorie, type d'item et quantité.
        """
        since = datetime.now() - timedelta(days=lookback_days)

        # Construire les filtres de base
        filters = [
            ItemPriceHistory.server_id == server_id,
            ItemPriceHistory.recorded_at >= since,
            ItemPriceHistory.price.isnot(None),
        ]

        # Ajouter le filtre de quantité si spécifié
        if quantity is not None:
            filters.append(ItemPriceHistory.quantity == quantity)

        # Récupérer tous les prix historiques
        prices_data = (
            session.query(
                ItemPriceHistory.gid,
                ItemPriceHistory.price,
            )
            .filter(*filters)
            .all()
        )

        # Calculer le prix moyen pour chaque item
        items_prices = {}
        items_price_counts = {}
        for gid, price in prices_data:
            if gid not in items_prices:
                items_prices[gid] = 0
                items_price_counts[gid] = 0
            items_prices[gid] += price
            items_price_counts[gid] += 1

        avg_prices = {
            gid: items_prices[gid] / items_price_counts[gid]
            for gid in items_prices
            if items_price_counts[gid] >= min_samples
        }

        # Filtrer les items par catégorie ou type si spécifié
        data_reader = DataReader()
        filtered_result_ids = None
        if category is not None or type_id is not None:
            filtered_result_ids = set(avg_prices.keys())

            if category is not None:
                category_gids = data_reader.item_ids_by_category.get(category, set())
                filtered_result_ids &= category_gids

            if type_id is not None:
                type_gids = data_reader.item_ids_by_type_id.get(type_id, set())
                filtered_result_ids &= type_gids

        profitable_crafts = []
        recipes = data_reader.recipes

        for recipe in recipes:
            result_id = recipe.resultId

            # Vérifier que l'item crafté se vend (a un historique de prix suffisant)
            if result_id not in avg_prices:
                continue

            # Filtrer par catégorie/type si spécifié
            if filtered_result_ids is not None and result_id not in filtered_result_ids:
                continue

            # Calculer le coût des ingrédients
            craft_cost = 0
            all_ingredients_available = True

            for ingredient_id, quantity_needed in zip(
                recipe.ingredientIds, recipe.quantities
            ):
                if ingredient_id not in avg_prices:
                    # Si un ingrédient n'a pas de prix, on ne peut pas calculer le coût
                    all_ingredients_available = False
                    break
                craft_cost += avg_prices[ingredient_id] * quantity_needed

            if not all_ingredients_available:
                continue

            # Prix de vente moyen de l'item crafté
            sell_price = avg_prices[result_id]

            # Profit brut
            profit = sell_price - craft_cost

            # Ignorer les recettes non rentables
            if profit <= 0:
                continue

            # Marge de profit en pourcentage
            if craft_cost > 0:
                profit_margin_pct = (profit / craft_cost) * 100
            else:
                profit_margin_pct = 0

            # Récupérer les informations de l'item
            item = data_reader.item_by_id.get(result_id)
            if not item or not item.nameId:
                continue

            item_name = I18N().name_by_id.get(item.nameId, f"Item {result_id}")

            # Détails des ingrédients
            ingredients_detail = []
            for ingredient_id, quantity_needed in zip(
                recipe.ingredientIds, recipe.quantities
            ):
                ingredient_item = data_reader.item_by_id.get(ingredient_id)
                ingredient_name = (
                    I18N().name_by_id.get(ingredient_item.nameId, f"Item {ingredient_id}")
                    if ingredient_item and ingredient_item.nameId
                    else f"Item {ingredient_id}"
                )
                ingredients_detail.append(
                    IngredientDetailSchema(
                        id=ingredient_id,
                        name=ingredient_name,
                        quantity=quantity_needed,
                        unit_price=round(avg_prices[ingredient_id], 2),
                        total_price=round(
                            avg_prices[ingredient_id] * quantity_needed, 2
                        ),
                    )
                )

            profitable_crafts.append(
                ProfitableCraftSchema(
                    result_id=result_id,
                    result_name=item_name,
                    sell_price=round(sell_price, 2),
                    craft_cost=round(craft_cost, 2),
                    profit=round(profit, 2),
                    profit_margin_pct=round(profit_margin_pct, 2),
                    ingredients=ingredients_detail,
                    samples=items_price_counts[result_id],
                )
            )

        # Trier par profit décroissant
        profitable_crafts.sort(key=lambda x: x.profit, reverse=True)

        return profitable_crafts[:top_n]
