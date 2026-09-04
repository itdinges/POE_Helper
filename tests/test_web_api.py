from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.application.services import read_market_item_history, read_market_snapshot
from app.infrastructure.market_store import MarketRowRecord, SQLiteMarketStore
from app.web.api import create_app


def _seed_market_data(db_path: Path) -> None:
    with SQLiteMarketStore(db_path=db_path) as store:
        store.save_market_rows(
            [
                MarketRowRecord(
                    league="Runes of Aldur",
                    market_type="Currency",
                    item_id="chaos-orb",
                    item_name="Chaos Orb",
                    image_path="/gen/image/chaos.png",
                    chaos_value=1.0,
                    primary_value=1.0,
                    fetched_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
                ),
                MarketRowRecord(
                    league="Runes of Aldur",
                    market_type="Currency",
                    item_id="divine-orb",
                    item_name="Divine Orb",
                    image_path="/gen/image/divine.png",
                    chaos_value=150.0,
                    primary_value=150.0,
                    fetched_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
                ),
            ]
        )
        store.refresh_market_item_stats("Runes of Aldur", "Currency")


def test_read_market_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "poe_market.db"
    _seed_market_data(db_path)

    snapshot = read_market_snapshot(league="Runes of Aldur", market_type="Currency", db_path=str(db_path))

    assert snapshot.ok is True
    assert snapshot.item_count == 2
    assert snapshot.top_entries[0].name == "Divine Orb"
    assert snapshot.rows[0].item_name in {"Chaos Orb", "Divine Orb"}
    assert snapshot.rows[0].icon_url is not None


def test_read_market_item_history(tmp_path: Path) -> None:
    db_path = tmp_path / "poe_market.db"
    _seed_market_data(db_path)

    history = read_market_item_history(
        league="Runes of Aldur",
        market_type="Currency",
        item_id="divine-orb",
        db_path=str(db_path),
    )

    assert history.ok is True
    assert history.item_name == "Divine Orb"
    assert history.icon_url is not None
    assert history.points
    assert history.points[0].chaos_value == 150.0


def test_fastapi_endpoints(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "poe_market.db"
    _seed_market_data(db_path)

    monkeypatch.setattr("app.web.api.read_market_snapshot", lambda **kwargs: read_market_snapshot(db_path=str(db_path), **kwargs))
    monkeypatch.setattr("app.web.api.read_market_item_history", lambda **kwargs: read_market_item_history(db_path=str(db_path), **kwargs))

    app = create_app()
    client = TestClient(app)

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json()["ok"] is True

    latest_response = client.get("/api/market/latest", params={"league": "Runes of Aldur", "market_type": "Currency"})
    assert latest_response.status_code == 200
    assert latest_response.json()["ok"] is True
    assert latest_response.json()["top_entries"][0]["name"] == "Divine Orb"

    history_response = client.get(
        "/api/market/history/divine-orb",
        params={"league": "Runes of Aldur", "market_type": "Currency"},
    )
    assert history_response.status_code == 200
    assert history_response.json()["item_name"] == "Divine Orb"