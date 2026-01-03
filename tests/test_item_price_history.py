from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.controllers.item_price_history import ItemPriceHistoryController
from src.models.base import Base
from src.models.item_price_history import ItemPriceHistory, QuantityEnum


@pytest.fixture()
def in_memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_is_price_resell_profitable_buy(in_memory_session):
    session = in_memory_session
    gid = 12345
    server_id = 1
    quantity = QuantityEnum.HUNDRED

    # Insert historical prices mostly higher than observed_price
    observed_price = 50
    higher_prices = [80, 75, 70, 60, 90, 100]
    now = datetime.now()
    items = []
    for i, p in enumerate(higher_prices):
        items.append(
            ItemPriceHistory(
                gid=gid,
                quantity=quantity,
                price=p,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )
    session.add_all(items)
    session.commit()

    result = ItemPriceHistoryController.is_price_resell_profitable(
        session,
        gid,
        quantity,
        server_id,
        observed_price,
        lookback_days=30,
        low_ratio=0.7,
        min_samples=3,
        fraction_higher_needed=0.5,
    )

    assert result["recommended_action"] == "buy"
    assert result["is_low"] is True
    assert result["samples"] >= 3


def test_is_price_resell_profitable_avoid(in_memory_session):
    session = in_memory_session
    gid = 99999
    server_id = 1
    quantity = QuantityEnum.HUNDRED

    # Insert historical prices mostly lower or similar
    observed_price = 100
    prices = [90, 95, 100, 105, 98]
    now = datetime.now()
    items = []
    for i, p in enumerate(prices):
        items.append(
            ItemPriceHistory(
                gid=gid,
                quantity=quantity,
                price=p,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )
    session.add_all(items)
    session.commit()

    result = ItemPriceHistoryController.is_price_resell_profitable(
        session,
        gid,
        quantity,
        server_id,
        observed_price,
        lookback_days=30,
        low_ratio=0.8,
        min_samples=3,
        fraction_higher_needed=0.6,
    )

    assert result["recommended_action"] in ("avoid", "consider")


def test_get_top_profitable_items_basic(in_memory_session):
    """Test que la fonction retourne les items les plus rentables triés correctement."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Item 1: Très rentable (prix varie de 50 à 150, moyenne ~100)
    item1_prices = [50, 80, 100, 120, 150]
    for i, price in enumerate(item1_prices):
        session.add(
            ItemPriceHistory(
                gid=1001,
                quantity=quantity,
                price=price,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Item 2: Moyennement rentable (prix varie de 80 à 120, moyenne ~100)
    item2_prices = [80, 90, 100, 110, 120]
    for i, price in enumerate(item2_prices):
        session.add(
            ItemPriceHistory(
                gid=1002,
                quantity=quantity,
                price=price,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Item 3: Peu rentable (prix stable autour de 100)
    item3_prices = [98, 99, 100, 101, 102]
    for i, price in enumerate(item3_prices):
        session.add(
            ItemPriceHistory(
                gid=1003,
                quantity=quantity,
                price=price,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    session.commit()

    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 3
    # Item 1 devrait être le plus rentable
    assert result[0]["gid"] == 1001
    assert result[0]["min_price"] == 50
    assert result[0]["max_price"] == 150
    assert result[0]["profit_potential"] > 0

    # Vérifier que les items sont triés par rentabilité décroissante
    assert (
        result[0]["profitability_score"]
        >= result[1]["profitability_score"]
        >= result[2]["profitability_score"]
    )


def test_get_top_profitable_items_min_samples_filter(in_memory_session):
    """Test que les items avec trop peu d'échantillons sont filtrés."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Item avec assez d'échantillons
    for i in range(10):
        session.add(
            ItemPriceHistory(
                gid=2001,
                quantity=quantity,
                price=100 + i * 10,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Item avec trop peu d'échantillons
    for i in range(3):
        session.add(
            ItemPriceHistory(
                gid=2002,
                quantity=quantity,
                price=100 + i * 10,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    session.commit()

    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=30, min_samples=5, top_n=50
    )

    # Seul l'item 2001 devrait être retourné
    assert len(result) == 1
    assert result[0]["gid"] == 2001
    assert result[0]["samples"] == 10


def test_get_top_profitable_items_top_n_limit(in_memory_session):
    """Test que le paramètre top_n limite correctement le nombre de résultats."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Créer 10 items avec des données
    for gid in range(3001, 3011):
        for i in range(6):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=quantity,
                    price=100 + i * 5,
                    recorded_at=now - timedelta(days=i + 1),
                    server_id=server_id,
                )
            )

    session.commit()

    # Demander seulement le top 3
    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=30, min_samples=5, top_n=3
    )

    assert len(result) == 3


def test_get_top_profitable_items_lookback_days(in_memory_session):
    """Test que le paramètre lookback_days filtre correctement les données anciennes."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Prix récents (dans les 10 derniers jours)
    for i in range(5):
        session.add(
            ItemPriceHistory(
                gid=4001,
                quantity=quantity,
                price=100,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Prix anciens (il y a plus de 20 jours)
    for i in range(5):
        session.add(
            ItemPriceHistory(
                gid=4001,
                quantity=quantity,
                price=200,
                recorded_at=now - timedelta(days=25 + i),
                server_id=server_id,
            )
        )

    session.commit()

    # Avec lookback de 15 jours, seuls les prix récents devraient être pris en compte
    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=15, min_samples=5, top_n=50
    )

    assert len(result) == 1
    # Le prix moyen devrait être autour de 100, pas 150 (moyenne de tous les prix)
    assert result[0]["avg_price"] == 100.0


def test_get_top_profitable_items_server_isolation(in_memory_session):
    """Test que les données sont bien isolées par serveur."""
    session = in_memory_session
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Données pour le serveur 1
    for i in range(6):
        session.add(
            ItemPriceHistory(
                gid=5001,
                quantity=quantity,
                price=100,
                recorded_at=now - timedelta(days=i + 1),
                server_id=1,
            )
        )

    # Données pour le serveur 2
    for i in range(6):
        session.add(
            ItemPriceHistory(
                gid=5002,
                quantity=quantity,
                price=200,
                recorded_at=now - timedelta(days=i + 1),
                server_id=2,
            )
        )

    session.commit()

    # Requête pour le serveur 1
    result_server1 = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id=1, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
    )

    # Requête pour le serveur 2
    result_server2 = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id=2, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
    )

    # Chaque serveur devrait avoir un seul item différent
    assert len(result_server1) == 1
    assert len(result_server2) == 1
    assert result_server1[0]["gid"] == 5001
    assert result_server2[0]["gid"] == 5002


def test_get_top_profitable_items_quantity_isolation(in_memory_session):
    """Test que les données sont bien isolées par quantité."""
    session = in_memory_session
    server_id = 1
    now = datetime.now()

    # Données pour quantité HUNDRED
    for i in range(6):
        session.add(
            ItemPriceHistory(
                gid=6001,
                quantity=QuantityEnum.HUNDRED,
                price=100,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Données pour quantité THOUSAND
    for i in range(6):
        session.add(
            ItemPriceHistory(
                gid=6002,
                quantity=QuantityEnum.THOUSAND,
                price=200,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    session.commit()

    # Requête pour quantité HUNDRED
    result_hundred = ItemPriceHistoryController.get_top_profitable_items(
        session,
        server_id=server_id,
        quantity=QuantityEnum.HUNDRED,
        lookback_days=30,
        min_samples=5,
        top_n=50,
    )

    # Requête pour quantité THOUSAND
    result_thousand = ItemPriceHistoryController.get_top_profitable_items(
        session,
        server_id=server_id,
        quantity=QuantityEnum.THOUSAND,
        lookback_days=30,
        min_samples=5,
        top_n=50,
    )

    assert len(result_hundred) == 1
    assert len(result_thousand) == 1
    assert result_hundred[0]["gid"] == 6001
    assert result_thousand[0]["gid"] == 6002


def test_get_top_profitable_items_empty_data(in_memory_session):
    """Test que la fonction retourne une liste vide quand il n'y a pas de données."""
    session = in_memory_session
    server_id = 999
    quantity = QuantityEnum.HUNDRED

    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert result == []


def test_get_top_profitable_items_calculations(in_memory_session):
    """Test que les calculs de profit et de volatilité sont corrects."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Item avec des prix connus pour vérifier les calculs
    prices = [100, 150, 200, 250, 300]
    for i, price in enumerate(prices):
        session.add(
            ItemPriceHistory(
                gid=7001,
                quantity=quantity,
                price=price,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    session.commit()

    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 1
    item = result[0]

    # Vérifications des calculs
    assert item["min_price"] == 100
    assert item["max_price"] == 300
    assert item["avg_price"] == 200.0  # (100+150+200+250+300)/5
    assert item["profit_potential"] == 100.0  # avg - min = 200 - 100
    assert item["profit_margin_pct"] == 100.0  # (100/100) * 100
    assert item["profitability_score"] == 10000.0  # 100 * 100
    assert item["samples"] == 5

    # Vérifier que la volatilité est calculée (écart-type)
    # Variance = ((100-200)² + (150-200)² + (200-200)² + (250-200)² + (300-200)²) / 5
    # = (10000 + 2500 + 0 + 2500 + 10000) / 5 = 5000
    # Écart-type = √5000 ≈ 70.71
    assert 70.0 <= item["volatility"] <= 71.0


def test_get_top_profitable_items_null_prices_filtered(in_memory_session):
    """Test que les prix NULL sont correctement filtrés."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Item avec des prix valides
    for i in range(5):
        session.add(
            ItemPriceHistory(
                gid=8001,
                quantity=quantity,
                price=100,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Ajouter des prix NULL (ne devraient pas être comptés)
    for i in range(3):
        session.add(
            ItemPriceHistory(
                gid=8001,
                quantity=quantity,
                price=None,
                recorded_at=now - timedelta(days=i + 6),
                server_id=server_id,
            )
        )

    session.commit()

    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 1
    # Seuls les 5 prix valides devraient être comptés
    assert result[0]["samples"] == 5
