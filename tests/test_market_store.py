from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.infrastructure.market_store import HoldingRecord, MarketRowRecord, SQLiteMarketStore


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


def test_market_store_reset_database_clears_stale_snapshot_files_and_sibling_db(tmp_path) -> None:
    db_path = tmp_path / "poe_market.db"
    stale_snapshot = tmp_path / "Runes_of_Aldur_Currency_20260904T085745Z.json"
    stale_snapshot.write_text('{"lines": []}', encoding="utf-8")
    stale_db = tmp_path / "dev_reset_test.db"
    stale_db.write_text("stale", encoding="utf-8")

    store = SQLiteMarketStore(db_path=str(db_path))
    try:
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
    finally:
        store.close()

    assert db_path.exists()
    assert not stale_snapshot.exists()
    assert not stale_db.exists()

    reopened = SQLiteMarketStore(db_path=str(db_path))
    try:
        assert reopened.get_latest_market_rows("Runes of Aldur", "Currency") == []
        assert reopened.get_market_types() == []
    finally:
        reopened.close()


def test_market_store_refreshes_item_stats_with_trend_windows(tmp_path) -> None:
    db_path = tmp_path / "market.db"
    store = SQLiteMarketStore(db_path=str(db_path))

    now = datetime(2026, 9, 1, 12, 0, 0)
    rows = [
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            image_path="/gen/image/divine.png",
            chaos_value=120.0,
            primary_value=120.0,
            volume_primary_value=50.0,
            sparkline_data=[-5.0, -2.0, 0.0, 2.0, 3.0, 4.0, 6.0],
            fetched_at=now - timedelta(hours=3),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            image_path="/gen/image/divine.png",
            chaos_value=90.0,
            primary_value=90.0,
            volume_primary_value=40.0,
            sparkline_data=[-5.0, -3.0, -1.0, 2.0, 1.0, 2.0, 4.0],
            fetched_at=now - timedelta(hours=2),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            image_path="/gen/image/divine.png",
            chaos_value=110.0,
            primary_value=110.0,
            volume_primary_value=80.0,
            sparkline_data=[-4.0, -1.0, 0.0, 2.0, 5.0, 6.5, 8.0],
            fetched_at=now,
        ),
    ]
    store.save_market_rows(rows)

    changed = store.refresh_market_item_stats("Runes of Aldur", "Currency")
    stats = store.get_market_item_stats("Runes of Aldur", "Currency")

    assert changed == 1
    assert len(stats) == 1
    assert stats[0].item_id == "divine"
    assert stats[0].trend_1h_percent == pytest.approx(22.2222222222)
    assert stats[0].trend_2h_percent == pytest.approx(22.2222222222)
    assert stats[0].trend_12h_percent is None
    assert stats[0].trend_24h_percent is None
    assert stats[0].short_term_reversal == "none"
    assert stats[0].liquidity_label in {"strong", "moderate"}
    assert stats[0].liquidity_score is not None
    assert stats[0].image_path == "/gen/image/divine.png"


def test_market_store_detects_bearish_reversal_when_24h_up_but_1h_2h_down(tmp_path) -> None:
    db_path = tmp_path / "market.db"
    store = SQLiteMarketStore(db_path=str(db_path))

    now = datetime(2026, 9, 1, 12, 0, 0)
    rows = [
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="exalt",
            item_name="Exalted Orb",
            chaos_value=100.0,
            primary_value=100.0,
            fetched_at=now - timedelta(hours=25),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="exalt",
            item_name="Exalted Orb",
            chaos_value=140.0,
            primary_value=140.0,
            fetched_at=now - timedelta(hours=2, minutes=30),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="exalt",
            item_name="Exalted Orb",
            chaos_value=130.0,
            primary_value=130.0,
            fetched_at=now - timedelta(hours=1, minutes=30),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="exalt",
            item_name="Exalted Orb",
            chaos_value=120.0,
            primary_value=120.0,
            fetched_at=now,
        ),
    ]
    store.save_market_rows(rows)
    store.refresh_market_item_stats("Runes of Aldur", "Currency")
    stats = store.get_market_item_stats("Runes of Aldur", "Currency")

    assert len(stats) == 1
    assert stats[0].trend_24h_percent > 0
    assert stats[0].trend_1h_percent < 0
    assert stats[0].trend_2h_percent < 0
    assert stats[0].short_term_reversal == "bearish_reversal"


def test_market_store_detects_bullish_reversal_when_24h_down_but_1h_2h_up(tmp_path) -> None:
    db_path = tmp_path / "market.db"
    store = SQLiteMarketStore(db_path=str(db_path))

    now = datetime(2026, 9, 1, 12, 0, 0)
    rows = [
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            chaos_value=200.0,
            primary_value=200.0,
            fetched_at=now - timedelta(hours=25),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            chaos_value=120.0,
            primary_value=120.0,
            fetched_at=now - timedelta(hours=2, minutes=30),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            chaos_value=130.0,
            primary_value=130.0,
            fetched_at=now - timedelta(hours=1, minutes=30),
        ),
        MarketRowRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            chaos_value=140.0,
            primary_value=140.0,
            fetched_at=now,
        ),
    ]
    store.save_market_rows(rows)
    store.refresh_market_item_stats("Runes of Aldur", "Currency")
    stats = store.get_market_item_stats("Runes of Aldur", "Currency")

    assert len(stats) == 1
    assert stats[0].trend_24h_percent < 0
    assert stats[0].trend_1h_percent > 0
    assert stats[0].trend_2h_percent > 0
    assert stats[0].short_term_reversal == "bullish_reversal"


def test_market_store_persists_holdings_and_joins_stats(tmp_path) -> None:
    db_path = tmp_path / "market.db"
    store = SQLiteMarketStore(db_path=str(db_path))

    now = datetime(2026, 9, 1, 12, 0, 0)
    store.save_market_rows(
        [
            MarketRowRecord(
                league="Runes of Aldur",
                market_type="Currency",
                item_id="divine",
                item_name="Divine Orb",
                image_path="/gen/image/divine.png",
                chaos_value=140.0,
                primary_value=140.0,
                fetched_at=now,
            )
        ]
    )
    store.refresh_market_item_stats("Runes of Aldur", "Currency")

    store.upsert_holding(
        HoldingRecord(
            league="Runes of Aldur",
            market_type="Currency",
            item_id="divine",
            item_name="Divine Orb",
            amount=25.0,
            updated_at=now,
        )
    )

    holdings = store.get_holdings("Runes of Aldur", "Currency")
    assert len(holdings) == 1
    assert holdings[0].item_id == "divine"
    assert holdings[0].amount == pytest.approx(25.0)

    joined_rows = store.get_market_item_holdings("Runes of Aldur", "Currency")
    assert len(joined_rows) == 1
    assert joined_rows[0].item_id == "divine"
    assert joined_rows[0].amount == pytest.approx(25.0)
    assert joined_rows[0].latest_chaos_value == pytest.approx(140.0)
