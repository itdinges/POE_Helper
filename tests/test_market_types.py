from __future__ import annotations

from app.domain.market_types import get_default_market_types, get_progression_market_types, load_market_type_config
from app.infrastructure.market_store import SQLiteMarketStore


def test_load_market_type_config() -> None:
    config = load_market_type_config("config/market_types.json")

    assert config.default_types == get_default_market_types("config/market_types.json")
    assert config.progression_types == get_progression_market_types("config/market_types.json")
    assert config.default_types
    assert config.progression_types


def test_default_market_types_are_available() -> None:
    config = load_market_type_config("config/market_types.json")
    defaults = get_default_market_types("config/market_types.json")

    assert defaults == config.default_types
    assert set(defaults).issubset(set(config.all_types))


def test_progression_market_types_are_available() -> None:
    config = load_market_type_config("config/market_types.json")
    progression = get_progression_market_types("config/market_types.json")

    assert progression == config.progression_types
    assert set(progression).issubset(set(config.all_types))


def test_market_type_catalog_syncs_into_sqlite(tmp_path) -> None:
    db_path = tmp_path / "fetch_types.db"
    config = load_market_type_config("config/market_types.json")
    store = SQLiteMarketStore(db_path=str(db_path))

    store.sync_market_types(config)

    assert set(store.get_market_types(category="default")) == set(config.default_types)
    assert set(store.get_market_types(category="progression")) == set(config.progression_types)
