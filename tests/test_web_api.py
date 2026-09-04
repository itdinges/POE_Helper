from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.application.services import read_holdings, read_market_item_history, read_market_snapshot
from app.contracts.responses import MarketWorkflowResponse
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


def test_holdings_endpoints(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "poe_market.db"
    _seed_market_data(db_path)

    monkeypatch.setattr("app.web.api.read_holdings", lambda **kwargs: read_holdings(db_path=str(db_path), **kwargs))
    from app.application.services import save_holdings as save_holdings_service

    monkeypatch.setattr("app.web.api.save_holdings", lambda **kwargs: save_holdings_service(db_path=str(db_path), **kwargs))

    app = create_app()
    client = TestClient(app)

    save_payload = {
        "league": "Runes of Aldur",
        "market_type": "Currency",
        "items": [
            {"item_id": "chaos-orb", "item_name": "Chaos Orb", "amount": 125},
            {"item_id": "divine-orb", "item_name": "Divine Orb", "amount": 4.5},
        ],
    }
    save_response = client.post("/api/holdings", json=save_payload)
    assert save_response.status_code == 200
    assert save_response.json()["ok"] is True

    get_response = client.get("/api/holdings", params={"league": "Runes of Aldur", "market_type": "Currency"})

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["ok"] is True
    amount_map = {item["item_id"]: item["amount"] for item in payload["items"]}
    assert amount_map["chaos-orb"] == 125
    assert amount_map["divine-orb"] == 4.5


def test_refresh_market_defaults_to_all_types(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_execute_market_workflow(**kwargs):
        captured.update(kwargs)
        return MarketWorkflowResponse(ok=True, market_data_source="refetch")

    monkeypatch.setattr("app.web.api.execute_market_workflow", fake_execute_market_workflow)

    app = create_app()
    client = TestClient(app)

    response = client.post("/api/market/refresh", params={"league": "Runes of Aldur"})

    assert response.status_code == 200
    assert captured["market_type"] == "all"
    assert captured["recommend"] is False