from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.application.services import (
    build_filter,
    build_score_profile_filter,
    execute_market_workflow,
    initialize_filter_manager,
    list_filters,
    load_holdings,
)
from app.domain.market_types import get_default_market_types, load_market_type_config
from app.domain.scoring import MarketItemScore
from app.filter_manager import FilterManager
from app.market import FlipResult, RouteStep


def test_initialize_filter_manager_success(tmp_path: Path) -> None:
    result, manager = initialize_filter_manager(str(tmp_path))

    assert result.ok is True
    assert manager is not None
    assert result.filter_directory == str(tmp_path.resolve())


def test_initialize_filter_manager_not_a_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("x", encoding="utf-8")

    result, manager = initialize_filter_manager(str(file_path))

    assert result.ok is False
    assert manager is None
    assert "not a directory" in (result.error or "").lower()


def test_list_filters_returns_sorted_files(tmp_path: Path) -> None:
    (tmp_path / "z_filter").write_text("z", encoding="utf-8")
    (tmp_path / "a_filter").write_text("a", encoding="utf-8")
    manager = FilterManager(filter_directory=str(tmp_path))

    response = list_filters(manager)

    assert response.ok is True
    assert response.filters == ["a_filter", "z_filter"]


def test_build_filter_requires_source_and_output(tmp_path: Path) -> None:
    manager = FilterManager(filter_directory=str(tmp_path))

    response = build_filter(manager, source=None, output=None, profile="mapping")

    assert response.ok is False
    assert response.error == "--build requires both --source and --output."


def test_build_filter_missing_source_file(tmp_path: Path) -> None:
    manager = FilterManager(filter_directory=str(tmp_path))

    response = build_filter(manager, source="missing_file", output="out", profile="mapping")

    assert response.ok is False
    assert response.error is not None
    assert "Filter not found" in response.error


def test_load_holdings_from_plain_map(tmp_path: Path) -> None:
    holdings_file = tmp_path / "holdings.json"
    holdings_file.write_text(json.dumps({"divine": 3, "exalt": "2.5"}), encoding="utf-8")

    parsed = load_holdings(str(holdings_file))

    assert parsed == {"divine": 3.0, "exalt": 2.5}


def test_load_holdings_from_stash_payload(tmp_path: Path) -> None:
    holdings_file = tmp_path / "stash_payload.json"
    holdings_file.write_text(
        json.dumps(
            {
                "numTabs": 1,
                "items": [
                    {"typeLine": "Exalted Orb", "stackSize": 8},
                    {"typeLine": "Exalted Orb", "stackSize": 5},
                    {"baseType": "Divine Orb", "stackSize": "2"},
                    {"name": "Chaos Orb"},
                ],
            }
        ),
        encoding="utf-8",
    )

    parsed = load_holdings(str(holdings_file))

    assert parsed is not None
    assert parsed["Exalted Orb"] == 13.0
    assert parsed["Divine Orb"] == 2.0
    assert parsed["Chaos Orb"] == 1.0


def test_execute_market_workflow_convert_and_flip(monkeypatch) -> None:
    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            return {"lines": [{"id": "wisdom", "primaryValue": 1.0}]}

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / "snapshot.json"

    def fake_summarize_market(payload, limit: int = 10):
        return [("Wisdom Scroll", 1.23)]

    def fake_convert(payload, amount: float, from_currency: str, to_currency: str):
        assert amount == 1000
        assert from_currency == "wisdom"
        assert to_currency == "chaos"
        return 0.6

    def fake_load_routes(route_file: str):
        return {
            "wisdom_to_aug": [RouteStep(from_currency="wisdom", to_currency="aug", from_amount=40, to_amount=1)]
        }

    def fake_simulate(payload, route_name: str, steps: list[RouteStep], start_amount: float):
        return FlipResult(
            route_name=route_name,
            start_currency="wisdom",
            start_amount=start_amount,
            end_currency="aug",
            end_amount=25.0,
            cost_chaos=0.6,
            revenue_chaos=0.8,
            profit_chaos=0.2,
            roi_percent=33.3,
            step_notes=["40 wisdom -> 1 aug; amount now 25.000"],
        )

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.summarize_market", fake_summarize_market)
    monkeypatch.setattr("app.application.services.convert_currency_amount", fake_convert)
    monkeypatch.setattr("app.application.services.load_flip_routes", fake_load_routes)
    monkeypatch.setattr("app.application.services.simulate_flip_route", fake_simulate)

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir="data/market",
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=True,
        from_currency="wisdom",
        to_currency="chaos",
        amount=1000,
        flip_route_file="config/flip_routes.example.json",
        flip_route_name="wisdom_to_aug",
    )

    assert response.ok is True
    assert response.snapshot_path is not None
    assert response.top_entries and response.top_entries[0].name == "Wisdom Scroll"
    assert response.conversion is not None
    assert response.conversion.converted_amount == 0.6
    assert response.flip_simulation is not None
    assert response.flip_simulation.route_name == "wisdom_to_aug"


def test_execute_market_workflow_vendor_no_opportunities(monkeypatch) -> None:
    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            return {"lines": [{"id": "wisdom", "primaryValue": 1.0}]}

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / "snapshot.json"

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.summarize_market", lambda payload, limit=10: [("Wisdom Scroll", 1.23)])
    monkeypatch.setattr("app.application.services.load_vendor_chaos_costs", lambda vendor_file: {"wisdom": 10.0})
    monkeypatch.setattr(
        "app.application.services.compare_vendor_to_market",
        lambda payload, vendor_costs, min_margin_chaos=0.0: [],
    )

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir="data/market",
        market_limit=10,
        vendor_file="config/vendor_prices.example.json",
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file=None,
        flip_route_name=None,
    )

    assert response.ok is True
    assert response.vendor_no_opportunities is True


def test_execute_market_workflow_flip_route_not_found(monkeypatch) -> None:
    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            return {"lines": [{"id": "wisdom", "primaryValue": 1.0}]}

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / "snapshot.json"

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.summarize_market", lambda payload, limit=10: [("Wisdom Scroll", 1.23)])
    monkeypatch.setattr("app.application.services.load_flip_routes", lambda route_file: {"known": []})

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir="data/market",
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file="config/flip_routes.example.json",
        flip_route_name="unknown",
    )

    assert response.ok is False
    assert response.error_stage == "flip"
    assert response.available_routes == ["known"]


def test_execute_market_workflow_fetch_error(monkeypatch, tmp_path: Path) -> None:
    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            raise RuntimeError("network down")

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / "snapshot.json"

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir=str(tmp_path),
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file=None,
        flip_route_name=None,
    )

    assert response.ok is False
    assert response.error_stage == "fetch"
    assert response.error is not None


def test_execute_market_workflow_fetches_default_configured_types(monkeypatch, tmp_path) -> None:
    config = load_market_type_config("config/market_types.json")
    expected_types = get_default_market_types("config/market_types.json")
    calls: list[str] = []

    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            calls.append(market_type)
            return {"lines": [{"id": "oracle", "primaryValue": 1.0}]}

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / f"{market_type}.json"

    class FakeStore:
        def __init__(self, db_path):
            self.rows = []
            self.db_path = db_path

        def sync_market_types(self, config, *, source="config"):
            return []

        def save_market_rows(self, rows):
            self.rows.extend(rows)

        def get_latest_market_rows(self, league: str, market_type: str):
            return []

        def refresh_market_item_stats(self, league: str, market_type: str):
            return 0

        def get_market_item_stats(self, league: str, market_type: str):
            return []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.SQLiteMarketStore", FakeStore)

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="all",
        market_out_dir=str(tmp_path),
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file=None,
        flip_route_name=None,
    )

    assert response.ok is True
    assert set(calls) == set(expected_types)
    assert set(calls).issubset(set(config.all_types))
    assert response.snapshot_path is not None


def test_execute_market_workflow_fetches_multiple_requested_types(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            calls.append(market_type)
            return {"lines": [{"id": market_type.lower(), "primaryValue": 1.0}]}

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / f"{market_type}.json"

    class FakeStore:
        def __init__(self, db_path):
            self.rows = []
            self.db_path = db_path

        def sync_market_types(self, config, *, source="config"):
            return []

        def save_market_rows(self, rows):
            self.rows.extend(rows)

        def get_latest_market_rows(self, league: str, market_type: str):
            return []

        def refresh_market_item_stats(self, league: str, market_type: str):
            return 0

        def get_market_item_stats(self, league: str, market_type: str):
            return []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.SQLiteMarketStore", FakeStore)
    monkeypatch.setattr(
        "app.application.services.summarize_market",
        lambda payload, limit=10: [(payload["lines"][0]["id"], 1.0)],
    )

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency,Fragments",
        market_out_dir=str(tmp_path),
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file=None,
        flip_route_name=None,
    )

    assert response.ok is True
    assert calls == ["Currency", "Fragments"]
    assert response.snapshot_path == str(tmp_path / "Currency.json")
    assert len(response.top_entries) == 2


def test_build_score_profile_filter_generates_managed_block(tmp_path: Path) -> None:
    manager = FilterManager(filter_directory=str(tmp_path))
    source_path = tmp_path / "base.filter"
    source_path.write_text("#name:base\n\nShow\n    Class \"Currency\"\n", encoding="utf-8")

    scores = [
        MarketItemScore(
            item_id="wisdom",
            item_name="Scroll of Wisdom",
            latest_value=0.3,
            previous_value=0.2,
            delta_percent=50.0,
            vendor_value=0.05,
            margin_chaos=0.25,
            trend="up",
            score=10.0,
            recommendation="show",
        )
    ]

    response = build_score_profile_filter(manager, source="base.filter", output="score_output.filter", scores=scores)

    assert response.ok is True
    output_path = tmp_path / "score_output.filter"
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "# score profile" in content
    assert "Scroll of Wisdom" in content


def test_execute_market_workflow_uses_fresh_cached_snapshot(monkeypatch, tmp_path: Path) -> None:
    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = tmp_path / f"runes-of-aldur_currency_{ts}.json"
    snapshot_payload = {
        "core": {
            "items": [
                {"id": "chaos", "name": "Chaos Orb"},
                {"id": "exalted", "name": "Exalted Orb"},
                {"id": "divine", "name": "Divine Orb"},
            ],
            "rates": {"chaos": 1.0},
        },
        "lines": [
            {"id": "chaos", "primaryValue": 1.0},
            {"id": "exalted", "primaryValue": 5.0},
            {"id": "divine", "primaryValue": 30.0},
        ],
    }
    snapshot_path.write_text(json.dumps(snapshot_payload), encoding="utf-8")

    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            raise AssertionError("fetch_overview should not be called for fresh cache")

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            raise AssertionError("save_snapshot should not be called for fresh cache")

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir=str(tmp_path),
        market_limit=5,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1000,
        flip_route_file=None,
        flip_route_name=None,
        recommend=True,
        source_currency="exalt",
    )

    assert response.ok is True
    assert response.market_data_source == "cache"
    assert response.snapshot_path == str(snapshot_path)


def test_execute_market_workflow_refetches_when_snapshot_stale(monkeypatch, tmp_path: Path) -> None:
    stale_ts = (datetime.now(UTC) - timedelta(hours=2)).strftime("%Y%m%dT%H%M%SZ")
    stale_snapshot_path = tmp_path / f"runes-of-aldur_currency_{stale_ts}.json"
    stale_snapshot_path.write_text(json.dumps({"lines": []}), encoding="utf-8")

    calls = {"fetch": 0, "save": 0}
    payload = {
        "core": {
            "items": [
                {"id": "chaos", "name": "Chaos Orb"},
                {"id": "exalted", "name": "Exalted Orb"},
                {"id": "divine", "name": "Divine Orb"},
            ],
            "rates": {"chaos": 1.0},
        },
        "lines": [
            {"id": "chaos", "primaryValue": 1.0},
            {"id": "exalted", "primaryValue": 5.0},
            {"id": "divine", "primaryValue": 30.0},
        ],
    }

    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            calls["fetch"] += 1
            return payload

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            calls["save"] += 1
            fresh = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            new_path = Path(output_directory) / f"runes-of-aldur_currency_{fresh}.json"
            new_path.write_text(json.dumps(payload), encoding="utf-8")
            return new_path

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir=str(tmp_path),
        market_limit=5,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1000,
        flip_route_file=None,
        flip_route_name=None,
        recommend=True,
        source_currency="exalt",
    )

    assert response.ok is True
    assert calls["fetch"] == 1
    assert calls["save"] == 1
    assert response.market_data_source == "refetch"


def test_execute_market_workflow_recommendations_include_market_type(monkeypatch, tmp_path: Path) -> None:
    payload_by_type = {
        "Currency": {
            "core": {
                "items": [
                    {"id": "chaos", "name": "Chaos Orb"},
                    {"id": "exalt", "name": "Exalted Orb"},
                    {"id": "divine", "name": "Divine Orb"},
                ],
                "rates": {"chaos": 1.0},
            },
            "lines": [
                {"id": "chaos", "primaryValue": 1.0},
                {"id": "exalt", "primaryValue": 5.0},
                {"id": "divine", "primaryValue": 30.0},
            ],
        },
        "Fragments": {
            "core": {
                "items": [
                    {"id": "chaos", "name": "Chaos Orb"},
                    {"id": "divine", "name": "Divine Orb"},
                    {"id": "frag_a", "name": "Fragment A"},
                ],
                "rates": {"chaos": 1.0},
            },
            "lines": [
                {"id": "chaos", "primaryValue": 1.0},
                {"id": "divine", "primaryValue": 30.0},
                {"id": "frag_a", "primaryValue": 10.0},
            ],
        },
    }

    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            return payload_by_type[market_type]

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / f"{market_type}.json"

    class FakeStore:
        def __init__(self, db_path):
            self.db_path = db_path

        def sync_market_types(self, config, *, source="config"):
            return []

        def save_market_rows(self, rows):
            return None

        def get_latest_market_rows(self, league: str, market_type: str):
            return []

        def refresh_market_item_stats(self, league: str, market_type: str):
            return 0

        def get_market_item_stats(self, league: str, market_type: str):
            return []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.SQLiteMarketStore", FakeStore)
    monkeypatch.setattr("app.application.services.summarize_market", lambda payload, limit=10: [])

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency,Fragments",
        market_out_dir=str(tmp_path),
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=100,
        flip_route_file=None,
        flip_route_name=None,
        recommend=True,
        source_currency="exalt",
        recommend_min_change=0.0,
        recommend_min_units=1.0,
    )

    assert response.ok is True
    assert response.recommendations
    recommendation_types = {rec.market_type for rec in response.recommendations}
    assert recommendation_types == {"Currency", "Fragments"}


def test_execute_market_workflow_routes_currency_to_oauth_source(monkeypatch, tmp_path: Path) -> None:
    calls = {"oauth": 0, "ninja": 0}

    class FakeOAuthClient:
        def fetch_overview(self, league: str, market_type: str):
            calls["oauth"] += 1
            return {
                "markets": [
                    {
                        "league": league,
                        "market_pair": [
                            "Metadata/Items/Currency/CurrencyRerollRare",
                            "Metadata/Items/Currency/CurrencyConvertToX",
                        ],
                        "lowest_ratio": {
                            "Metadata/Items/Currency/CurrencyRerollRare": 120,
                            "Metadata/Items/Currency/CurrencyConvertToX": 1,
                        },
                    }
                ]
            }

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str, source_tag: str | None = None):
            suffix = f"_{source_tag}" if source_tag else ""
            return Path(output_directory) / f"{market_type}{suffix}.json"

    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            calls["ninja"] += 1
            return {"lines": [{"id": "frag", "primaryValue": 1.0}]}

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / f"{market_type}.json"

    class FakeStore:
        def __init__(self, db_path):
            self.db_path = db_path

        def sync_market_types(self, config, *, source="config"):
            return []

        def save_market_rows(self, rows):
            return None

        def get_latest_market_rows(self, league: str, market_type: str):
            return []

        def refresh_market_item_stats(self, league: str, market_type: str):
            return 0

        def get_market_item_stats(self, league: str, market_type: str):
            return []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        "app.application.services.OAuthCurrencyExchangeClient.from_environment",
        lambda: FakeOAuthClient(),
    )
    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)
    monkeypatch.setattr("app.application.services.SQLiteMarketStore", FakeStore)
    monkeypatch.setattr("app.application.services.summarize_market", lambda payload, limit=10: [("x", 1.0)])

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency,Fragments",
        market_out_dir=str(tmp_path),
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file=None,
        flip_route_name=None,
        market_source="oauth_cx",
    )

    assert response.ok is True
    assert calls["oauth"] == 1
    assert calls["ninja"] == 1


def test_execute_market_workflow_oauth_source_requires_credentials(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("POE_CX_CLIENT_ID", raising=False)
    monkeypatch.delenv("POE_CX_CLIENT_SECRET", raising=False)

    response = execute_market_workflow(
        league="Runes of Aldur",
        market_type="Currency",
        market_out_dir=str(tmp_path),
        market_limit=10,
        vendor_file=None,
        min_margin=0.0,
        convert=False,
        from_currency=None,
        to_currency=None,
        amount=1.0,
        flip_route_file=None,
        flip_route_name=None,
        market_source="oauth_cx",
    )

    assert response.ok is False
    assert response.error_stage == "fetch"
    assert response.error is not None
    assert "POE_CX_CLIENT_ID" in response.error
