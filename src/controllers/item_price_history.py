from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

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
    def get_sales_speed_from_prices(session: Session, gid: int, quantity: QuantityEnum):
        records = (
            session.query(ItemPriceHistory)
            .filter(ItemPriceHistory.gid == gid)
            .filter(ItemPriceHistory.quantity == quantity)
            .order_by(ItemPriceHistory.recorded_at.asc())
            .all()
        )

        if len(records) < 2:
            return None

        increases = 0
        prev_price = records[0].price
        for curr_price_history in records[1:]:
            if curr_price_history.price > prev_price:
                increases += 1
            prev_price = curr_price_history.price

        speed = increases / len(records)
        return speed

    @staticmethod
    def get_avg_price(session: Session, gid: int, quantity: QuantityEnum, days=7):
        since = datetime.now() - timedelta(days=days)
        return (
            session.query(func.avg(ItemPriceHistory.price))
            .filter(ItemPriceHistory.gid == gid)
            .filter(ItemPriceHistory.quantity == quantity)
            .filter(ItemPriceHistory.recorded_at >= since)
            .scalar()
        )

    @staticmethod
    def get_last_price_percentage_change(
        session: Session, gid: int, quantity: QuantityEnum
    ):
        sub = (
            session.query(ItemPriceHistory)
            .filter(ItemPriceHistory.gid == gid)
            .filter(ItemPriceHistory.quantity == quantity)
            .order_by(ItemPriceHistory.recorded_at.desc())
            .limit(2)
            .all()
        )
        if len(sub) < 2:
            return None
        last, prev = sub[0], sub[1]
        change = (last.price - prev.price) / prev.price * 100
        return change
