import random
from datetime import datetime, timedelta

from sqlalchemy import Float, case, func, select
from sqlalchemy.orm import Session

from D3Database.data_center.data_reader import DataReader
from src.models.item_price_history import ItemPriceHistory, QuantityEnum
from src.schemas.item_price_history import CreateItemPriceHistorySchema


class ItemPriceHistoryController:
    @staticmethod
    def _generate_random_item_history(session: Session):
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
