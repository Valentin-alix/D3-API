from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from D3Database.enums.category_item_enum import CategoryEnum
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

    assert result.recommended_action == "buy"
    assert result.is_low is True
    assert result.samples >= 3


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

    assert result.recommended_action in ("avoid", "consider")


@patch("src.controllers.item_price_history.DataReader")
@patch("src.controllers.item_price_history.I18N")
def test_get_top_profitable_items_basic(mock_i18n, mock_data_reader, in_memory_session):
    """Test que la fonction retourne les items les plus rentables triés correctement."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock setup
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance
    mock_reader_instance.item_by_id = {
        1001: MagicMock(nameId=1),
        1002: MagicMock(nameId=2),
        1003: MagicMock(nameId=3),
    }

    mock_i18n_instance = MagicMock()
    mock_i18n.return_value = mock_i18n_instance
    mock_i18n_instance.name_by_id = {1: "Item 1001", 2: "Item 1002", 3: "Item 1003"}

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
        session, server_id, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 3
    # Item 1 devrait être le plus rentable
    assert result[0].gid == 1001
    assert result[0].min_price == 50
    assert result[0].max_price == 150
    assert result[0].profit_potential > 0

    # Vérifier que les items sont triés par rentabilité décroissante
    assert (
        result[0].profitability_score
        >= result[1].profitability_score
        >= result[2].profitability_score
    )


@patch("src.controllers.item_price_history.DataReader")
@patch("src.controllers.item_price_history.I18N")
def test_get_top_profitable_items_min_samples_filter(mock_i18n, mock_data_reader, in_memory_session):
    """Test que les items avec trop peu d'échantillons sont filtrés."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock setup
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance
    mock_reader_instance.item_by_id = {
        2001: MagicMock(nameId=1),
        2002: MagicMock(nameId=2),
    }

    mock_i18n_instance = MagicMock()
    mock_i18n.return_value = mock_i18n_instance
    mock_i18n_instance.name_by_id = {1: "Item 2001", 2: "Item 2002"}

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
        session, server_id, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
    )

    # Seul l'item 2001 devrait être retourné
    assert len(result) == 1
    assert result[0].gid == 2001
    assert result[0].samples == 10


@patch("src.controllers.item_price_history.DataReader")
@patch("src.controllers.item_price_history.I18N")
def test_get_top_profitable_items_top_n_limit(mock_i18n, mock_data_reader, in_memory_session):
    """Test que le paramètre top_n limite correctement le nombre de résultats."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock setup
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance
    mock_reader_instance.item_by_id = {gid: MagicMock(nameId=gid) for gid in range(3001, 3011)}

    mock_i18n_instance = MagicMock()
    mock_i18n.return_value = mock_i18n_instance
    mock_i18n_instance.name_by_id = {gid: f"Item {gid}" for gid in range(3001, 3011)}

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


@patch("src.controllers.item_price_history.DataReader")
@patch("src.controllers.item_price_history.I18N")
def test_get_top_profitable_items_lookback_days(mock_i18n, mock_data_reader, in_memory_session):
    """Test que le paramètre lookback_days filtre correctement les données anciennes."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock setup
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance
    mock_reader_instance.item_by_id = {4001: MagicMock(nameId=1)}

    mock_i18n_instance = MagicMock()
    mock_i18n.return_value = mock_i18n_instance
    mock_i18n_instance.name_by_id = {1: "Item 4001"}

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
    assert result[0].avg_price == 100.0


@patch("src.controllers.item_price_history.DataReader")
@patch("src.controllers.item_price_history.I18N")
def test_get_top_profitable_items_server_isolation(mock_i18n, mock_data_reader, in_memory_session):
    """Test que les données sont bien isolées par serveur."""
    session = in_memory_session
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock setup
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance
    mock_reader_instance.item_by_id = {
        5001: MagicMock(nameId=1),
        5002: MagicMock(nameId=2),
    }

    mock_i18n_instance = MagicMock()
    mock_i18n.return_value = mock_i18n_instance
    mock_i18n_instance.name_by_id = {1: "Item 5001", 2: "Item 5002"}

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
    assert result_server1[0].gid == 5001
    assert result_server2[0].gid == 5002


@patch("src.controllers.item_price_history.DataReader")
@patch("src.controllers.item_price_history.I18N")
def test_get_top_profitable_items_quantity_isolation(mock_i18n, mock_data_reader, in_memory_session):
    """Test que les données sont bien isolées par quantité."""
    session = in_memory_session
    server_id = 1
    now = datetime.now()

    # Mock setup
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance
    mock_reader_instance.item_by_id = {
        6001: MagicMock(nameId=1),
        6002: MagicMock(nameId=2),
    }

    mock_i18n_instance = MagicMock()
    mock_i18n.return_value = mock_i18n_instance
    mock_i18n_instance.name_by_id = {1: "Item 6001", 2: "Item 6002"}

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
    assert result_hundred[0].gid == 6001
    assert result_thousand[0].gid == 6002


def test_get_top_profitable_items_empty_data(in_memory_session):
    """Test que la fonction retourne une liste vide quand il n'y a pas de données."""
    session = in_memory_session
    server_id = 999
    quantity = QuantityEnum.HUNDRED

    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
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
        session, server_id, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 1
    item = result[0]

    # Vérifications des calculs
    assert item.min_price == 100
    assert item.max_price == 300
    assert item.avg_price == 200.0  # (100+150+200+250+300)/5
    assert item.profit_potential == 100.0  # avg - min = 200 - 100
    assert item.profit_margin_pct == 100.0  # (100/100) * 100
    assert item.profitability_score == 10000.0  # 100 * 100
    assert item.samples == 5

    # Vérifier que la volatilité est calculée (écart-type)
    # Variance = ((100-200)² + (150-200)² + (200-200)² + (250-200)² + (300-200)²) / 5
    # = (10000 + 2500 + 0 + 2500 + 10000) / 5 = 5000
    # Écart-type = √5000 ≈ 70.71
    assert 70.0 <= item.volatility <= 71.0


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
        session, server_id, quantity=quantity, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 1
    # Seuls les 5 prix valides devraient être comptés
    assert result[0].samples == 5


# ==================== TESTS POUR LES NOUVEAUX FILTRES ====================


def test_get_top_profitable_items_with_quantity_none(in_memory_session):
    """Test que quantity=None retourne les données pour toutes les quantités."""
    session = in_memory_session
    server_id = 1
    now = datetime.now()

    # Item avec prix pour quantité HUNDRED
    for i in range(3):
        session.add(
            ItemPriceHistory(
                gid=9001,
                quantity=QuantityEnum.HUNDRED,
                price=100 + i * 10,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # Item avec prix pour quantité THOUSAND
    for i in range(3):
        session.add(
            ItemPriceHistory(
                gid=9001,
                quantity=QuantityEnum.THOUSAND,
                price=200 + i * 10,
                recorded_at=now - timedelta(days=i + 4),
                server_id=server_id,
            )
        )

    session.commit()

    # Avec quantity=None, toutes les quantités devraient être incluses
    result = ItemPriceHistoryController.get_top_profitable_items(
        session, server_id, quantity=None, lookback_days=30, min_samples=5, top_n=50
    )

    assert len(result) == 1
    assert result[0].gid == 9001
    # Devrait avoir 6 échantillons (3 HUNDRED + 3 THOUSAND)
    assert result[0].samples == 6


@patch("src.controllers.item_price_history.DataReader")
def test_get_top_profitable_items_filter_by_category(mock_data_reader, in_memory_session):
    """Test le filtrage par catégorie d'items."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock du DataReader
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance

    # Configurer le mock pour simuler des catégories
    # Item 10001 est dans RESOURCES (category 2)
    # Item 10002 est dans CONSUMABLES (category 1)
    mock_reader_instance.item_ids_by_category = {
        CategoryEnum.RESOURCES: {10001},
        CategoryEnum.CONSUMABLES: {10002},
    }
    mock_reader_instance.item_by_id = {
        10001: MagicMock(nameId=1),
        10002: MagicMock(nameId=2),
    }

    # Créer des données pour les deux items
    for gid in [10001, 10002]:
        for i in range(6):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=quantity,
                    price=100 + i * 10,
                    recorded_at=now - timedelta(days=i + 1),
                    server_id=server_id,
                )
            )

    session.commit()

    # Filtrer seulement RESOURCES
    with patch("src.controllers.item_price_history.I18N") as mock_i18n:
        mock_i18n_instance = MagicMock()
        mock_i18n.return_value = mock_i18n_instance
        mock_i18n_instance.name_by_id = {1: "Resource Item", 2: "Consumable Item"}

        result = ItemPriceHistoryController.get_top_profitable_items(
            session,
            server_id,
            quantity,
            lookback_days=30,
            min_samples=5,
            top_n=50,
            category=CategoryEnum.RESOURCES,
        )

    # Seul l'item 10001 (RESOURCES) devrait être retourné
    assert len(result) == 1
    assert result[0].gid == 10001


@patch("src.controllers.item_price_history.DataReader")
def test_get_top_profitable_items_filter_by_type_id(mock_data_reader, in_memory_session):
    """Test le filtrage par type d'item."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock du DataReader
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance

    # Configurer le mock pour simuler des types
    # Item 11001 est de type 42
    # Item 11002 est de type 43
    mock_reader_instance.item_ids_by_type_id = {
        42: {11001},
        43: {11002},
    }
    mock_reader_instance.item_by_id = {
        11001: MagicMock(nameId=1),
        11002: MagicMock(nameId=2),
    }

    # Créer des données pour les deux items
    for gid in [11001, 11002]:
        for i in range(6):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=quantity,
                    price=100 + i * 10,
                    recorded_at=now - timedelta(days=i + 1),
                    server_id=server_id,
                )
            )

    session.commit()

    # Filtrer seulement type_id=42
    with patch("src.controllers.item_price_history.I18N") as mock_i18n:
        mock_i18n_instance = MagicMock()
        mock_i18n.return_value = mock_i18n_instance
        mock_i18n_instance.name_by_id = {1: "Type 42 Item", 2: "Type 43 Item"}

        result = ItemPriceHistoryController.get_top_profitable_items(
            session,
            server_id,
            quantity,
            lookback_days=30,
            min_samples=5,
            top_n=50,
            type_id=42,
        )

    # Seul l'item 11001 (type 42) devrait être retourné
    assert len(result) == 1
    assert result[0].gid == 11001


@patch("src.controllers.item_price_history.DataReader")
def test_get_top_profitable_items_filter_by_category_and_type(
    mock_data_reader, in_memory_session
):
    """Test le filtrage combiné par catégorie ET type d'item."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock du DataReader
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance

    # Item 12001: RESOURCES (2) + type 42
    # Item 12002: RESOURCES (2) + type 43
    # Item 12003: CONSUMABLES (1) + type 42
    mock_reader_instance.item_ids_by_category = {
        CategoryEnum.RESOURCES: {12001, 12002},
        CategoryEnum.CONSUMABLES: {12003},
    }
    mock_reader_instance.item_ids_by_type_id = {
        42: {12001, 12003},
        43: {12002},
    }
    mock_reader_instance.item_by_id = {
        12001: MagicMock(nameId=1),
        12002: MagicMock(nameId=2),
        12003: MagicMock(nameId=3),
    }

    # Créer des données pour les trois items
    for gid in [12001, 12002, 12003]:
        for i in range(6):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=quantity,
                    price=100 + i * 10,
                    recorded_at=now - timedelta(days=i + 1),
                    server_id=server_id,
                )
            )

    session.commit()

    # Filtrer RESOURCES + type 42 -> seul 12001 devrait correspondre
    with patch("src.controllers.item_price_history.I18N") as mock_i18n:
        mock_i18n_instance = MagicMock()
        mock_i18n.return_value = mock_i18n_instance
        mock_i18n_instance.name_by_id = {
            1: "Resource Type 42",
            2: "Resource Type 43",
            3: "Consumable Type 42",
        }

        result = ItemPriceHistoryController.get_top_profitable_items(
            session,
            server_id,
            quantity,
            lookback_days=30,
            min_samples=5,
            top_n=50,
            category=CategoryEnum.RESOURCES,
            type_id=42,
        )

    # Seul l'item 12001 devrait être retourné (RESOURCES ET type 42)
    assert len(result) == 1
    assert result[0].gid == 12001


def test_evaluate_resell_with_quantity_none(in_memory_session):
    """Test evaluate_resell avec quantity=None (toutes les quantités)."""
    session = in_memory_session
    gid = 13001
    server_id = 1
    observed_price = 50
    now = datetime.now()

    # Ajouter des prix pour différentes quantités
    # HUNDRED: prix élevés
    for i in range(3):
        session.add(
            ItemPriceHistory(
                gid=gid,
                quantity=QuantityEnum.HUNDRED,
                price=80 + i * 5,
                recorded_at=now - timedelta(days=i + 1),
                server_id=server_id,
            )
        )

    # THOUSAND: prix élevés aussi
    for i in range(3):
        session.add(
            ItemPriceHistory(
                gid=gid,
                quantity=QuantityEnum.THOUSAND,
                price=90 + i * 5,
                recorded_at=now - timedelta(days=i + 4),
                server_id=server_id,
            )
        )

    session.commit()

    # Avec quantity=None, toutes les quantités sont évaluées
    result = ItemPriceHistoryController.is_price_resell_profitable(
        session,
        gid,
        quantity=None,
        server_id=server_id,
        observed_price=observed_price,
        lookback_days=30,
        low_ratio=0.7,
        min_samples=3,
        fraction_higher_needed=0.5,
    )

    assert result.samples == 6  # 3 HUNDRED + 3 THOUSAND
    assert result.recommended_action == "buy"  # Prix observé bien plus bas
    assert result.is_low is True


@patch("src.controllers.item_price_history.DataReader")
def test_get_top_profitable_crafts_filter_by_category(mock_data_reader, in_memory_session):
    """Test le filtrage des crafts par catégorie."""
    session = in_memory_session
    server_id = 1
    quantity = QuantityEnum.HUNDRED
    now = datetime.now()

    # Mock du DataReader
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance

    # Créer des recettes mockées
    recipe1 = MagicMock(
        resultId=14001, ingredientIds=[14100, 14101], quantities=[1, 2]
    )
    recipe2 = MagicMock(
        resultId=14002, ingredientIds=[14100, 14101], quantities=[1, 2]
    )

    mock_reader_instance.recipes = [recipe1, recipe2]

    # 14001 est EQUIPMENT, 14002 est CONSUMABLES
    mock_reader_instance.item_ids_by_category = {
        CategoryEnum.EQUIPMENT: {14001},
        CategoryEnum.CONSUMABLES: {14002},
    }

    # Configurer les items mockés
    mock_reader_instance.item_by_id = {
        14001: MagicMock(nameId=1),
        14002: MagicMock(nameId=2),
        14100: MagicMock(nameId=100),
        14101: MagicMock(nameId=101),
    }

    # Créer des prix pour les résultats et ingrédients
    # Ingrédient 14100: 10 kamas
    # Ingrédient 14101: 20 kamas
    # Résultat 14001: 100 kamas (rentable: 100 - (10 + 2*20) = 50 de profit)
    # Résultat 14002: 120 kamas (rentable: 120 - (10 + 2*20) = 70 de profit)
    items_prices = {
        14100: 10,
        14101: 20,
        14001: 100,
        14002: 120,
    }

    for gid, price in items_prices.items():
        for i in range(6):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=quantity,
                    price=price,
                    recorded_at=now - timedelta(days=i + 1),
                    server_id=server_id,
                )
            )

    session.commit()

    # Filtrer seulement EQUIPMENT
    with patch("src.controllers.item_price_history.I18N") as mock_i18n:
        mock_i18n_instance = MagicMock()
        mock_i18n.return_value = mock_i18n_instance
        mock_i18n_instance.name_by_id = {
            1: "Equipment Craft",
            2: "Consumable Craft",
            100: "Ingredient 1",
            101: "Ingredient 2",
        }

        result = ItemPriceHistoryController.get_top_profitable_crafts(
            session,
            server_id,
            quantity,
            lookback_days=30,
            min_samples=5,
            top_n=50,
            category=CategoryEnum.EQUIPMENT,
        )

    # Seul le craft 14001 (EQUIPMENT) devrait être retourné
    assert len(result) == 1
    assert result[0].result_id == 14001


@patch("src.controllers.item_price_history.DataReader")
def test_get_top_profitable_crafts_with_quantity_none(mock_data_reader, in_memory_session):
    """Test get_top_profitable_crafts avec quantity=None."""
    session = in_memory_session
    server_id = 1
    now = datetime.now()

    # Mock du DataReader
    mock_reader_instance = MagicMock()
    mock_data_reader.return_value = mock_reader_instance

    # Recette mockée
    recipe = MagicMock(resultId=15001, ingredientIds=[15100, 15101], quantities=[1, 1])
    mock_reader_instance.recipes = [recipe]

    mock_reader_instance.item_by_id = {
        15001: MagicMock(nameId=1),
        15100: MagicMock(nameId=100),
        15101: MagicMock(nameId=101),
    }

    # Créer des prix pour différentes quantités
    # Cela devrait augmenter le nombre d'échantillons
    items_prices = {15100: 10, 15101: 20, 15001: 100}

    for gid, price in items_prices.items():
        # 3 prix pour HUNDRED
        for i in range(3):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=QuantityEnum.HUNDRED,
                    price=price,
                    recorded_at=now - timedelta(days=i + 1),
                    server_id=server_id,
                )
            )
        # 3 prix pour THOUSAND
        for i in range(3):
            session.add(
                ItemPriceHistory(
                    gid=gid,
                    quantity=QuantityEnum.THOUSAND,
                    price=price,
                    recorded_at=now - timedelta(days=i + 4),
                    server_id=server_id,
                )
            )

    session.commit()

    with patch("src.controllers.item_price_history.I18N") as mock_i18n:
        mock_i18n_instance = MagicMock()
        mock_i18n.return_value = mock_i18n_instance
        mock_i18n_instance.name_by_id = {
            1: "Crafted Item",
            100: "Ingredient 1",
            101: "Ingredient 2",
        }

        result = ItemPriceHistoryController.get_top_profitable_crafts(
            session,
            server_id,
            quantity=None,
            lookback_days=30,
            min_samples=5,
            top_n=50,
        )

    # Le craft devrait être retourné avec 6 échantillons (3 HUNDRED + 3 THOUSAND)
    assert len(result) == 1
    assert result[0].result_id == 15001
    assert result[0].samples == 6
