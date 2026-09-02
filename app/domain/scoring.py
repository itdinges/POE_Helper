from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MarketItemScore:
    item_id: str
    item_name: str
    latest_value: float
    previous_value: float | None
    delta_percent: float
    vendor_value: float | None
    margin_chaos: float | None
    trend: str
    score: float
    recommendation: str


def score_market_item(
    *,
    item_id: str,
    item_name: str,
    latest_value: float,
    previous_value: float | None,
    vendor_value: float | None,
) -> MarketItemScore:
    if previous_value is not None and previous_value != 0:
        delta_percent = ((latest_value - previous_value) / previous_value) * 100.0
    else:
        delta_percent = 0.0

    if delta_percent > 0:
        trend = "up"
    elif delta_percent < 0:
        trend = "down"
    else:
        trend = "flat"

    margin_chaos = None if vendor_value is None else latest_value - vendor_value

    score = delta_percent * 1.5
    if margin_chaos is not None:
        score += margin_chaos * 10.0

    if vendor_value is not None:
        if margin_chaos is not None and margin_chaos >= 0.25:
            recommendation = "show"
        elif margin_chaos is not None and margin_chaos >= 0.05:
            recommendation = "watch"
        else:
            recommendation = "hide"
    else:
        if delta_percent >= 20.0:
            recommendation = "watch"
        elif delta_percent <= -10.0:
            recommendation = "hide"
        else:
            recommendation = "watch"

    return MarketItemScore(
        item_id=item_id,
        item_name=item_name,
        latest_value=latest_value,
        previous_value=previous_value,
        delta_percent=delta_percent,
        vendor_value=vendor_value,
        margin_chaos=margin_chaos,
        trend=trend,
        score=score,
        recommendation=recommendation,
    )
