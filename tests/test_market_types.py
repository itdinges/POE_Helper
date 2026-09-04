from __future__ import annotations

from app.domain.market_types import get_default_market_types, get_progression_market_types, load_market_type_config
from app.infrastructure.market_store import SQLiteMarketStore


def test_load_market_type_config() -> None:
    config = load_market_type_config("config/market_types.json")

    assert [item.display for item in config.items] == get_default_market_types("config/market_types.json")
    assert [item.display for item in config.progression_types] == get_progression_market_types("config/market_types.json")
    assert config.items
    assert config.progression_types


def test_default_market_types_are_available() -> None:
    config = load_market_type_config("config/market_types.json")
    defaults = get_default_market_types("config/market_types.json")

    assert defaults == [item.display for item in config.items]
    assert set(defaults).issubset(set(config.all_types))


def test_market_type_config_supports_display_and_fetch_values() -> None:
    config = load_market_type_config("config/market_types.json")
    lineage_entry = config.find_entry("Lineage Gems")

    assert lineage_entry is not None
    assert lineage_entry.name == "Lineage Gems"
    assert lineage_entry.fetch_name == "LineageSupportGems"
    assert lineage_entry.fetch_url == "https://poe.ninja/poe2/api/economy/exchange/current/overview"

    by_fetch_value = config.find_entry("LineageSupportGems")
    assert by_fetch_value is not None
    assert by_fetch_value.name == "Lineage Gems"

    tablets_entry = config.find_entry("Unique Tablets")
    assert tablets_entry is not None
    assert tablets_entry.fetch_url == "https://poe.ninja/poe2/api/economy/stash/current/item/overview"


def test_progression_market_types_are_available() -> None:
    config = load_market_type_config("config/market_types.json")
    progression = get_progression_market_types("config/market_types.json")

    assert progression == [item.display for item in config.progression_types]
    assert set(progression).issubset(set(config.all_types))


def test_market_type_catalog_syncs_into_sqlite(tmp_path) -> None:
    db_path = tmp_path / "fetch_types.db"
    config = load_market_type_config("config/market_types.json")
    store = SQLiteMarketStore(db_path=str(db_path))

    store.sync_market_types(config)

    assert set(store.get_market_types(category="items")) == set(get_default_market_types("config/market_types.json"))
    assert set(store.get_market_types(category="progression")) == set(get_progression_market_types("config/market_types.json"))
