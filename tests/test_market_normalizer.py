from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.adapters.market_adapter import normalize_market_rows_for_store


def _load_fixture() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "poe_ninja_currency_overview.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_normalize_market_rows_for_store() -> None:
    payload = {
        "core": {
            "items": [
                {
                    "id": "divine",
                    "name": "Divine Orb",
                    "image": "/gen/image/test/divine.png",
                }
            ],
            "rates": {"chaos": 10.0},
        },
        "lines": [
            {"id": "divine", "primaryValue": 1.0},
        ],
    }
    fetched_at = datetime(2026, 8, 29, 12, 0, 0)

    rows = normalize_market_rows_for_store(
        payload,
        league="Runes of Aldur",
        market_type="Currency",
        fetched_at=fetched_at,
    )

    assert len(rows) == 1
    assert rows[0].item_name == "Divine Orb"
    assert rows[0].item_id == "divine"
    assert rows[0].chaos_value == 10.0
    assert rows[0].primary_value == 1.0
    assert rows[0].fetched_at == fetched_at
    assert rows[0].vendor_value is None
    assert rows[0].image_path == "/gen/image/test/divine.png"
