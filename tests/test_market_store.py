from __future__ import annotations

from datetime import datetime, timedelta

from app.infrastructure.market_store import MarketRowRecord, SQLiteMarketStore


def test_market_store_persists_and_reads_latest_rows(tmp_path) -> None:
    db_path = tmp_path / "market.db"
    store = SQLiteMarketStore(db_path=str(db_path))

    first_time = datetime(2026, 8, 29, 12, 0, 0)
    second_time = first_time + timedelta(minutes=5)

    rows = [
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="wisdom",
            item_name="Scroll of Wisdom",
            chaos_value=0.25,
            primary_value=1.0,
            fetched_at=first_time,
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="aug",
            item_name="Orb of Augmentation",
            chaos_value=0.9,
            primary_value=1.0,
            fetched_at=first_time,
        ),
    ]
    store.save_market_rows(rows)

    store.save_market_rows(
        [
            MarketRowRecord(
                league="Runes of Aldur",
                market_type="Currency",
                item_id="wisdom",
                item_name="Scroll of Wisdom",
                chaos_value=0.3,
                primary_value=1.0,
                fetched_at=second_time,
            )
        ]
    )

    latest = store.get_latest_market_rows("Runes of Aldur", "Currency")
    assert {row.item_id: row.chaos_value for row in latest} == {"wisdom": 0.3, "aug": 0.9}

    history = store.get_item_history("Runes of Aldur", "Currency", "wisdom")
    assert len(history) == 2
    assert [row.chaos_value for row in history] == [0.25, 0.3]

    snapshot_id = store.save_snapshot_record(
        league="Runes of Aldur",
        market_type="Currency",
        source_file="data/market/test.json",
        fetched_at=second_time,
    )
    assert snapshot_id > 0


def test_market_store_reset_database_clears_rows_and_catalog(tmp_path) -> None:
    db_path = tmp_path / "market.db"
    store = SQLiteMarketStore(db_path=str(db_path))

    store.save_market_rows(
        [
            MarketRowRecord(
                league="Runes of Aldur",
                market_type="Currency",
                item_id="wisdom",
                item_name="Scroll of Wisdom",
                chaos_value=0.25,
                primary_value=1.0,
                fetched_at=datetime(2026, 8, 29, 12, 0, 0),
            )
        ]
    )

    store.reset_database()

    assert store.get_latest_market_rows("Runes of Aldur", "Currency") == []
    assert store.get_market_types() == []
