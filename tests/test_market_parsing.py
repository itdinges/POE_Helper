from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.market import (
    FlipResult,
    MarketClient,
    RouteStep,
    build_currency_recommendations,
    build_price_lookup,
    compare_vendor_to_market,
    convert_currency_amount,
    extract_lines,
    load_flip_routes,
    load_vendor_chaos_costs,
    parse_market_rows,
    simulate_flip_route,
    summarize_market,
)


def _load_fixture() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "poe_ninja_currency_overview.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_extract_lines_non_list_returns_empty() -> None:
    assert extract_lines({"lines": {"bad": "shape"}}) == []


def test_parse_market_rows_and_summarize_from_fixture() -> None:
    payload = _load_fixture()

    rows = parse_market_rows(payload)

    assert len(rows) == 5
    price_map = build_price_lookup(rows)
    assert price_map["divine"] == 10.0
    assert price_map["chaos"] == 1.0

    top = summarize_market(payload, limit=2)
    assert top[0][0] == "Divine Orb"
    assert top[0][1] == 10.0


def test_parse_market_rows_uses_top_level_items_for_images() -> None:
    payload = {
        "core": {
            "items": [
                {"id": "divine", "name": "Divine Orb", "image": "/gen/image/core-divine.png"},
            ],
            "rates": {"chaos": 10.0},
        },
        "lines": [
            {"id": "alch", "primaryValue": 0.1},
        ],
        "items": [
            {
                "id": "alch",
                "name": "Orb of Alchemy",
                "image": "/gen/image/top-alch.png",
                "detailsId": "orb-of-alchemy",
            }
        ],
    }

    rows = parse_market_rows(payload)

    assert len(rows) == 1
    assert rows[0].id == "alch"
    assert rows[0].name == "Orb of Alchemy"
    assert rows[0].image_path == "/gen/image/top-alch.png"


def test_convert_currency_amount_and_missing_currency_error() -> None:
    payload = _load_fixture()

    converted = convert_currency_amount(payload, amount=1000, from_currency="wisdom", to_currency="chaos")
    assert converted == pytest.approx(0.5)

    with pytest.raises(ValueError, match="Currency not found"):
        convert_currency_amount(payload, amount=1, from_currency="missing", to_currency="chaos")


def test_compare_vendor_to_market_by_name_and_id() -> None:
    payload = _load_fixture()
    vendor = {
        "Scroll of Wisdom": 0.0002,
        "aug": 0.001,
    }

    opportunities = compare_vendor_to_market(payload, vendor, min_margin_chaos=0.0)

    assert [row.name for row in opportunities] == ["Orb of Augmentation", "Scroll of Wisdom"]
    assert opportunities[0].margin_chaos > opportunities[1].margin_chaos


def test_build_currency_recommendations_ranks_by_units_received() -> None:
    payload = {
        "core": {
            "items": [
                {"id": "divine", "name": "Divine Orb"},
                {"id": "exalt", "name": "Exalted Orb"},
                {"id": "chaos", "name": "Chaos Orb"},
            ],
            "rates": {"chaos": 1.0},
            "primary": "divine",
            "secondary": "chaos",
        },
        "lines": [
            {"id": "divine", "primaryValue": 30.0},
            {"id": "exalt", "primaryValue": 5.0},
            {"id": "chaos", "primaryValue": 1.0},
        ],
    }

    recommendations = build_currency_recommendations(
        payload,
        source_currency="chaos",
        amount=100.0,
        previous_prices={"chaos": 1.0, "divine": 20.0, "exalt": 10.0},
        holdings={"Exalted Orb": 5.0},
        trend_signals={
            "exalt": {
                "trend_1h_percent": -1.0,
                "trend_2h_percent": 2.0,
                "trend_12h_percent": 3.5,
                "trend_24h_percent": 8.0,
                "short_term_reversal": "bearish_reversal",
            }
        },
        min_change_percent=0.5,
        min_trade_units=1.0,
        max_results=3,
    )

    assert recommendations[0]["target_currency"] == "exalt"
    assert recommendations[0]["market_type"] == "Currency"
    assert recommendations[0]["converted_amount"] == pytest.approx(20.0)
    assert recommendations[1]["target_currency"] == "divine"
    assert recommendations[1]["converted_amount"] == pytest.approx(3.0)
    assert recommendations[0]["value_divine"] == pytest.approx(100.0 / 30.0)
    assert recommendations[0]["action"] == "buy"
    assert recommendations[0]["actionable_action"] == "buy"
    assert recommendations[0]["owned_target_units"] == pytest.approx(5.0)
    assert recommendations[0]["whole_units_owned"] == 5
    assert recommendations[0]["spent_source_units"] == pytest.approx(100.0)
    assert recommendations[0]["leftover_source_units"] == pytest.approx(0.0)
    assert recommendations[0]["trend_1h_percent"] == pytest.approx(-1.0)
    assert recommendations[0]["short_term_reversal"] == "bearish_reversal"


def test_load_vendor_chaos_costs_formats_and_errors(tmp_path: Path) -> None:
    list_style = tmp_path / "vendor_list.json"
    list_style.write_text(
        json.dumps({"items": [{"name": "wisdom", "vendor_chaos_cost": 0.001}]}),
        encoding="utf-8",
    )
    assert load_vendor_chaos_costs(str(list_style)) == {"wisdom": 0.001}

    map_style = tmp_path / "vendor_map.json"
    map_style.write_text(json.dumps({"wisdom": 0.001, "aug": "0.002"}), encoding="utf-8")
    assert load_vendor_chaos_costs(str(map_style)) == {"wisdom": 0.001, "aug": 0.002}

    invalid = tmp_path / "invalid_vendor.json"
    invalid.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ValueError, match="Vendor file must"):
        load_vendor_chaos_costs(str(invalid))


def test_load_flip_routes_and_simulate_route(tmp_path: Path) -> None:
    payload = _load_fixture()
    routes_file = tmp_path / "routes.json"
    routes_file.write_text(
        json.dumps(
            {
                "routes": [
                    {
                        "name": "wisdom_to_aug",
                        "steps": [
                            {"from": "wisdom", "to": "aug", "from_amount": 40, "to_amount": 1}
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    routes = load_flip_routes(str(routes_file))
    result = simulate_flip_route(payload, "wisdom_to_aug", routes["wisdom_to_aug"], start_amount=4000)

    assert isinstance(result, FlipResult)
    assert result.end_amount == pytest.approx(100.0)
    assert result.end_currency == "aug"


def test_simulate_flip_route_error_paths(tmp_path: Path) -> None:
    payload = _load_fixture()

    with pytest.raises(ValueError, match="start_amount"):
        simulate_flip_route(payload, "bad", [], start_amount=0)

    mismatch_steps = [
        RouteStep(from_currency="chaos", to_currency="aug", from_amount=2.0, to_amount=1.0),
        RouteStep(from_currency="wisdom", to_currency="chaos", from_amount=3.0, to_amount=1.0),
    ]
    with pytest.raises(ValueError, match="Route currency mismatch"):
        simulate_flip_route(payload, "mismatch", mismatch_steps, start_amount=10)


def test_market_client_fetch_and_save_snapshot(monkeypatch, tmp_path: Path) -> None:
    payload = _load_fixture()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return payload

    def fake_get(url: str, params: dict, timeout: int):
        assert "overview" in url
        assert params["league"] == "Runes of Aldur"
        assert params["type"] == "Currency"
        assert timeout == 20
        return FakeResponse()

    monkeypatch.setattr("app.market.requests.get", fake_get)

    client = MarketClient()
    fetched = client.fetch_overview("Runes of Aldur", "Currency")
    snapshot = client.save_snapshot(fetched, str(tmp_path), "Runes of Aldur", "Currency")

    assert snapshot.exists()
    assert "runes-of-aldur_currency_" in snapshot.name
