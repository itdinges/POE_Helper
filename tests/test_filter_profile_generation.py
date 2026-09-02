from __future__ import annotations

from app.domain.filter_profiles import build_score_profile_rules
from app.domain.scoring import MarketItemScore


def test_build_score_profile_rules_groups_by_recommendation() -> None:
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
        ),
        MarketItemScore(
            item_id="orb",
            item_name="Orb of Augmentation",
            latest_value=0.85,
            previous_value=0.9,
            delta_percent=-5.56,
            vendor_value=None,
            margin_chaos=None,
            trend="down",
            score=1.0,
            recommendation="watch",
        ),
        MarketItemScore(
            item_id="trash",
            item_name="Low Value Currency",
            latest_value=0.02,
            previous_value=0.03,
            delta_percent=-33.33,
            vendor_value=0.02,
            margin_chaos=0.0,
            trend="down",
            score=-5.0,
            recommendation="hide",
        ),
    ]

    rules = build_score_profile_rules(scores)
    joined = "\n".join(rules)

    assert "# score profile" in joined
    assert "Scroll of Wisdom" in joined
    assert "Orb of Augmentation" in joined
    assert "Low Value Currency" in joined
    assert "Show" in joined
    assert "Hide" in joined
    assert "Watch" not in joined
    assert '    BaseType "Scroll of Wisdom"' in joined
    assert '    BaseType "Low Value Currency"' in joined
    assert '# watch entries omitted from generated filter output' in joined
    assert '    # watch: "Orb of Augmentation"' in joined
