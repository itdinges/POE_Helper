from __future__ import annotations

import pytest

from app.domain.scoring import score_market_item


def test_score_market_item_uses_margin_and_trend() -> None:
    score = score_market_item(
        item_id="wisdom",
        item_name="Scroll of Wisdom",
        latest_value=0.30,
        previous_value=0.20,
        vendor_value=0.05,
    )

    assert score.delta_percent == pytest.approx(50.0)
    assert score.margin_chaos == pytest.approx(0.25)
    assert score.trend == "up"
    assert score.score > 0
    assert score.recommendation in {"show", "watch"}


def test_score_market_item_without_vendor_value_is_cautious() -> None:
    score = score_market_item(
        item_id="orb",
        item_name="Orb of Augmentation",
        latest_value=0.85,
        previous_value=0.9,
        vendor_value=None,
    )

    assert score.delta_percent == pytest.approx(-5.555555555555555)
    assert score.margin_chaos is None
    assert score.trend == "down"
    assert score.recommendation in {"watch", "hide"}
