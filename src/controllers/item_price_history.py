import random
from datetime import datetime, timedelta

from sqlalchemy import Float, case, func, select
from sqlalchemy.orm import Session

from D3Database.data_center.data_reader import DataReader
from D3Database.data_center.i18n import I18N
from src.models.item_price_history import ItemPriceHistory, QuantityEnum
from src.schemas.item_price_history import CreateItemPriceHistorySchema


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
        quantity: QuantityEnum,
        server_id: int,
        observed_price: float,
        lookback_days: int = 30,
        low_ratio: float = 0.6,
        min_samples: int = 5,
        fraction_higher_needed: float = 0.5,
    ) -> dict:
        """Détermine si `observed_price` est suffisamment bas par rapport aux prix
        historiques pour envisager un achat/revente rentable.

        Retourne un dict contenant des métriques et une recommandation :
        - is_low: bool
        - avg_price, median_price, samples, fraction_higher
        - recommended_action: 'buy'|'consider'|'avoid'
        - reason: texte court
        """
        since = datetime.now() - timedelta(days=lookback_days)

        prices_rows = (
            session.query(ItemPriceHistory.price)
            .filter(
                ItemPriceHistory.gid == gid,
                ItemPriceHistory.quantity == quantity,
                ItemPriceHistory.server_id == server_id,
                ItemPriceHistory.recorded_at >= since,
            )
            .order_by(ItemPriceHistory.recorded_at.desc())
            .all()
        )

        prices = [row[0] for row in prices_rows]
        samples = len(prices)

        if samples == 0:
            return {
                "is_low": False,
                "avg_price": None,
                "median_price": None,
                "samples": 0,
                "fraction_higher": 0.0,
                "recommended_action": "avoid",
                "reason": "no_data",
            }

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

        return {
            "is_low": is_low,
            "avg_price": avg_price,
            "median_price": median_price,
            "samples": samples,
            "fraction_higher": fraction_higher,
            "recommended_action": recommended_action,
            "reason": reason,
        }

    @staticmethod
    def get_top_profitable_items(
        session: Session,
        server_id: int,
        quantity: QuantityEnum = QuantityEnum.HUNDRED,
        lookback_days: int = 30,
        min_samples: int = 5,
        top_n: int = 50,
    ) -> list[dict]:
        """Retourne un classement des items les plus rentables à acheter pour revendre.

        Calcule pour chaque item ayant des données historiques :
        - Le prix moyen actuel (derniers enregistrements)
        - Le prix minimum observé
        - Le potentiel de profit (différence entre prix moyen et prix minimum)
        - La volatilité des prix (écart-type)

        Retourne une liste triée par rentabilité potentielle.
        """
        since = datetime.now() - timedelta(days=lookback_days)

        prices_data = (
            session.query(
                ItemPriceHistory.gid,
                ItemPriceHistory.price,
                ItemPriceHistory.recorded_at,
            )
            .filter(
                ItemPriceHistory.quantity == quantity,
                ItemPriceHistory.server_id == server_id,
                ItemPriceHistory.recorded_at >= since,
                ItemPriceHistory.price.isnot(None),
            )
            .order_by(ItemPriceHistory.gid, ItemPriceHistory.recorded_at)
            .all()
        )

        items_data = {}
        for gid, price, _ in prices_data:
            if gid not in items_data:
                items_data[gid] = []
            items_data[gid].append(price)

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

            item_name = I18N().name_by_id[DataReader().item_by_id[gid].nameId]

            profitable_items.append(
                {
                    "gid": gid,
                    "name": item_name,
                    "avg_price": round(avg_price, 2),
                    "min_price": min_price,
                    "max_price": max_price,
                    "profit_potential": round(profit_potential, 2),
                    "profit_margin_pct": round(profit_margin_pct, 2),
                    "profitability_score": round(profitability_score, 2),
                    "volatility": round(std_dev, 2),
                    "samples": len(prices),
                }
            )

        profitable_items.sort(key=lambda x: x["profitability_score"], reverse=True)

        return profitable_items[:top_n]
