from __future__ import annotations

from pathlib import Path

from app.application.services import (
    build_filter,
    build_score_profile_filter,
    execute_market_workflow,
    initialize_filter_manager,
    list_filters,
)
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


def test_execute_market_workflow_fetch_error(monkeypatch) -> None:
    class FakeMarketClient:
        def fetch_overview(self, league: str, market_type: str):
            raise RuntimeError("network down")

        def save_snapshot(self, payload, output_directory: str, league: str, market_type: str):
            return Path(output_directory) / "snapshot.json"

    monkeypatch.setattr("app.application.services.MarketClient", FakeMarketClient)

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
        flip_route_file=None,
        flip_route_name=None,
    )

    assert response.ok is False
    assert response.error_stage == "fetch"
    assert response.error is not None


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
