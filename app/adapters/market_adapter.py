from __future__ import annotations

from datetime import datetime

from app.infrastructure.market_store import MarketRowRecord
from app.market import parse_market_rows


def normalize_market_rows_for_store(
    payload: dict,
    *,
    league: str,
    market_type: str,
    fetched_at: datetime,
) -> list[MarketRowRecord]:
    rows = parse_market_rows(payload)
    normalized: list[MarketRowRecord] = []
    for row in rows:
        normalized.append(
            MarketRowRecord(
                league=league,
                market_type=market_type,
                item_id=row.id,
                item_name=row.name,
                image_path=row.image_path,
                chaos_value=float(row.chaos_value),
                primary_value=float(row.primary_value),
                volume_primary_value=row.volume_primary_value,
                sparkline_data=row.sparkline_data or [],
                fetched_at=fetched_at,
                vendor_value=None,
            )
        )
    return normalized
