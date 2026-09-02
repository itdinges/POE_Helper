from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


API_BASE_URL = "https://poe.ninja/poe2/api/economy/exchange/current/overview"
log = logging.getLogger("poe-helper.market")


@dataclass
class MarketOpportunity:
    name: str
    market_chaos_value: float
    vendor_chaos_cost: float
    margin_chaos: float


@dataclass
class MarketRow:
    id: str
    name: str
    chaos_value: float
    primary_value: float


@dataclass
class RouteStep:
    from_currency: str
    to_currency: str
    from_amount: float
    to_amount: float


@dataclass
class FlipResult:
    route_name: str
    start_currency: str
    start_amount: float
    end_currency: str
    end_amount: float
    cost_chaos: float
    revenue_chaos: float
    profit_chaos: float
    roi_percent: float
    step_notes: list[str]


class MarketClient:
    def __init__(self, base_url: str = API_BASE_URL, timeout_seconds: int = 20) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def fetch_overview(self, league: str, market_type: str) -> dict[str, Any]:
        log.info(
            "Fetching market overview (league=%s, type=%s)",
            league,
            market_type,
            extra={"league": league, "market_type": market_type},
        )
        response = requests.get(
            self.base_url,
            params={"league": league, "type": market_type},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected market payload format: expected JSON object")
        log.info(
            "Market overview fetched (league=%s, type=%s, lines=%s)",
            league,
            market_type,
            len(payload.get("lines", [])) if isinstance(payload.get("lines"), list) else 0,
            extra={"line_count": len(payload.get("lines", [])) if isinstance(payload.get("lines"), list) else 0},
        )
        return payload

    def save_snapshot(
        self,
        payload: dict[str, Any],
        output_directory: str,
        league: str,
        market_type: str,
        source_tag: str | None = None,
    ) -> Path:
        output_dir = Path(output_directory).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        league_slug = _sanitize_filename(league)
        type_slug = _sanitize_filename(market_type)
        source_slug = _sanitize_filename(source_tag) if source_tag else None
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        if source_slug:
            file_path = output_dir / f"{league_slug}_{type_slug}_{source_slug}_{timestamp}.json"
        else:
            file_path = output_dir / f"{league_slug}_{type_slug}_{timestamp}.json"
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.info(
            "Market snapshot saved (league=%s, type=%s, path=%s)",
            league,
            market_type,
            str(file_path),
            extra={"path": str(file_path)},
        )
        return file_path


def extract_lines(payload: dict[str, Any]) -> list[dict[str, Any]]:
    lines = payload.get("lines", [])
    if not isinstance(lines, list):
        return []
    return [line for line in lines if isinstance(line, dict)]


def summarize_market(payload: dict[str, Any], limit: int = 10) -> list[tuple[str, float]]:
    rows = parse_market_rows(payload)
    items = [(row.name, row.chaos_value) for row in rows]
    items.sort(key=lambda row: row[1], reverse=True)
    return items[: max(1, limit)]


def load_vendor_chaos_costs(vendor_file: str) -> dict[str, float]:
    path = Path(vendor_file).expanduser().resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(raw, dict):
        if "items" in raw and isinstance(raw["items"], list):
            costs: dict[str, float] = {}
            for row in raw["items"]:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "")).strip()
                if not name:
                    continue
                cost = _to_float(row.get("vendor_chaos_cost"))
                if cost is None:
                    continue
                costs[name] = cost
            return costs

        costs = {}
        for name, cost_raw in raw.items():
            cost = _to_float(cost_raw)
            if cost is None:
                continue
            costs[str(name)] = cost
        return costs

    raise ValueError("Vendor file must be a JSON object or an object with an 'items' list")


def compare_vendor_to_market(
    payload: dict[str, Any], vendor_costs: dict[str, float], min_margin_chaos: float = 0.0
) -> list[MarketOpportunity]:
    opportunities: list[MarketOpportunity] = []
    for row in parse_market_rows(payload):
        name = row.name
        market_chaos_value = row.chaos_value

        vendor_chaos_cost = vendor_costs.get(name)
        if vendor_chaos_cost is None:
            vendor_chaos_cost = vendor_costs.get(row.id)
        if vendor_chaos_cost is None:
            continue

        margin = market_chaos_value - vendor_chaos_cost
        if margin < min_margin_chaos:
            continue

        opportunities.append(
            MarketOpportunity(
                name=name,
                market_chaos_value=market_chaos_value,
                vendor_chaos_cost=vendor_chaos_cost,
                margin_chaos=margin,
            )
        )

    opportunities.sort(key=lambda row: row.margin_chaos, reverse=True)
    return opportunities


def convert_currency_amount(
    payload: dict[str, Any], amount: float, from_currency: str, to_currency: str
) -> float:
    rows = parse_market_rows(payload)
    price_map = build_price_lookup(rows)
    from_price = _lookup_price(price_map, from_currency)
    to_price = _lookup_price(price_map, to_currency)
    if from_price is None:
        raise ValueError(f"Currency not found in market snapshot: {from_currency}")
    if to_price is None:
        raise ValueError(f"Currency not found in market snapshot: {to_currency}")
    if to_price == 0:
        raise ValueError(f"Target currency has zero chaos value: {to_currency}")
    return (amount * from_price) / to_price


def build_currency_recommendations(
    payload: dict[str, Any],
    *,
    market_type: str = "Currency",
    source_currency: str,
    amount: float,
    previous_prices: dict[str, float] | None = None,
    holdings: dict[str, float] | None = None,
    trend_signals: dict[str, dict[str, float | str | None]] | None = None,
    min_change_percent: float = 0.5,
    min_trade_units: float = 1.0,
    whole_unit_trades: bool = True,
    source_price_override: float | None = None,
    previous_source_price_override: float | None = None,
    divine_price_override: float | None = None,
    exalt_price_override: float | None = None,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    rows = parse_market_rows(payload)
    price_map = build_price_lookup(rows)
    source_price = _lookup_price(price_map, source_currency)
    if source_price is None:
        source_price = source_price_override
    if source_price is None:
        raise ValueError(f"Currency not found in market snapshot: {source_currency}")

    divine_price = _lookup_price(price_map, "divine")
    if divine_price is None:
        divine_price = divine_price_override
    if divine_price is None or divine_price <= 0:
        raise ValueError("Divine Orb is required to compute Divine-equivalent values")

    normalized_holdings = _normalize_previous_prices(holdings)

    recommendations: list[dict[str, Any]] = []
    for row in rows:
        if _normalize_key(row.id) == _normalize_key(source_currency):
            continue

        target_price = row.chaos_value
        if target_price <= 0:
            continue

        converted_amount_raw = (amount * source_price) / target_price
        whole_units_affordable = int(math.floor(converted_amount_raw))
        tradable_units = float(whole_units_affordable) if whole_unit_trades else converted_amount_raw
        final_chaos_value = tradable_units * target_price
        value_divine = final_chaos_value / divine_price
        current_ratio = target_price / source_price if source_price > 0 else None
        spent_source_units = tradable_units * current_ratio if current_ratio is not None else 0.0
        leftover_source_units = max(0.0, amount - spent_source_units)

        previous_ratio: float | None = None
        ratio_change_percent: float | None = None
        if previous_prices:
            previous_source_price = _lookup_price(previous_prices, source_currency)
            if previous_source_price is None:
                previous_source_price = previous_source_price_override
            previous_target_price = _lookup_price(previous_prices, row.id)
            if previous_source_price and previous_target_price and previous_source_price > 0:
                previous_ratio = previous_target_price / previous_source_price
                if previous_ratio != 0:
                    ratio_change_percent = ((current_ratio - previous_ratio) / previous_ratio) * 100.0

        action = "hold"
        if ratio_change_percent is not None:
            if ratio_change_percent <= -abs(min_change_percent):
                action = "buy"
            elif ratio_change_percent >= abs(min_change_percent):
                action = "sell"

        owned_target_units = _lookup_price(normalized_holdings, row.id) or _lookup_price(normalized_holdings, row.name) or 0.0
        whole_units_owned = int(math.floor(owned_target_units))
        affordable_units = tradable_units
        required_whole_units = int(math.ceil(max(1.0, min_trade_units)))
        is_affordable = whole_units_affordable >= required_whole_units
        can_sell = whole_units_owned >= required_whole_units

        actionable_action = "hold"
        if action == "buy" and is_affordable:
            actionable_action = "buy"
        elif action == "sell" and can_sell:
            actionable_action = "sell"

        signal = trend_signals.get(row.id) if trend_signals else None
        if signal is None and trend_signals:
            signal = trend_signals.get(row.name)
        trend_1h = signal.get("trend_1h_percent") if signal else None
        trend_2h = signal.get("trend_2h_percent") if signal else None
        trend_12h = signal.get("trend_12h_percent") if signal else None
        trend_24h = signal.get("trend_24h_percent") if signal else None
        short_term_reversal = signal.get("short_term_reversal") if signal else None
        trend_alignment = _build_trend_alignment(action, trend_1h)

        exalt_price = _lookup_price(price_map, "exalt")
        if exalt_price is None:
            exalt_price = exalt_price_override

        recommendations.append(
            {
                "market_type": market_type,
                "source_currency": source_currency,
                "target_currency": row.id,
                "target_name": row.name,
                "amount": amount,
                "converted_amount": tradable_units,
                "target_price": target_price,
                "value_chaos": final_chaos_value,
                "value_divine": value_divine,
                "value_exalt": final_chaos_value / exalt_price if exalt_price else None,
                "spent_source_units": spent_source_units,
                "leftover_source_units": leftover_source_units,
                "action": action,
                "current_ratio": current_ratio,
                "previous_ratio": previous_ratio,
                "ratio_change_percent": ratio_change_percent,
                "affordable_units": affordable_units,
                "whole_units_affordable": whole_units_affordable,
                "is_affordable": is_affordable,
                "owned_target_units": owned_target_units,
                "whole_units_owned": whole_units_owned,
                "can_sell": can_sell,
                "actionable_action": actionable_action,
                "trend_1h_percent": trend_1h,
                "trend_2h_percent": trend_2h,
                "trend_12h_percent": trend_12h,
                "trend_24h_percent": trend_24h,
                "short_term_reversal": short_term_reversal,
                "trend_alignment": trend_alignment,
            }
        )

    recommendations.sort(
        key=lambda item: (
            abs(item["ratio_change_percent"]) if item["ratio_change_percent"] is not None else 0.0,
            item["converted_amount"],
            item["target_price"],
        ),
        reverse=True,
    )
    return recommendations[: max(1, max_results)]


def load_flip_routes(route_file: str) -> dict[str, list[RouteStep]]:
    path = Path(route_file).expanduser().resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Route file must be a JSON object")

    routes_raw = raw.get("routes")
    if not isinstance(routes_raw, list):
        raise ValueError("Route file must contain a 'routes' list")

    routes: dict[str, list[RouteStep]] = {}
    for route in routes_raw:
        if not isinstance(route, dict):
            continue
        name = str(route.get("name", "")).strip()
        steps_raw = route.get("steps")
        if not name or not isinstance(steps_raw, list):
            continue

        steps: list[RouteStep] = []
        for step in steps_raw:
            if not isinstance(step, dict):
                continue

            from_currency = str(step.get("from", "")).strip()
            to_currency = str(step.get("to", "")).strip()
            from_amount = _to_float(step.get("from_amount"))
            to_amount = _to_float(step.get("to_amount"))

            if not from_currency or not to_currency:
                continue
            if from_amount is None or to_amount is None or from_amount <= 0 or to_amount <= 0:
                continue

            steps.append(
                RouteStep(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    from_amount=from_amount,
                    to_amount=to_amount,
                )
            )

        if steps:
            routes[name] = steps

    if not routes:
        raise ValueError("No valid routes found in route file")

    return routes


def simulate_flip_route(
    payload: dict[str, Any], route_name: str, steps: list[RouteStep], start_amount: float
) -> FlipResult:
    if start_amount <= 0:
        raise ValueError("start_amount must be greater than zero")

    rows = parse_market_rows(payload)
    price_map = build_price_lookup(rows)

    start_currency = steps[0].from_currency
    start_price = _lookup_price(price_map, start_currency)
    if start_price is None:
        raise ValueError(f"Start currency not found in market snapshot: {start_currency}")

    amount = start_amount
    current_currency = start_currency
    step_notes: list[str] = []
    for step in steps:
        if _normalize_key(step.from_currency) != _normalize_key(current_currency):
            raise ValueError(
                f"Route currency mismatch in step {step.from_currency}->{step.to_currency}; "
                f"current currency is {current_currency}"
            )

        amount = amount * (step.to_amount / step.from_amount)
        current_currency = step.to_currency
        step_notes.append(
            f"{step.from_amount:g} {step.from_currency} -> {step.to_amount:g} {step.to_currency}; amount now {amount:.3f}"
        )

    end_currency = current_currency
    end_price = _lookup_price(price_map, end_currency)
    if end_price is None:
        raise ValueError(
            f"End currency not found in market snapshot: {end_currency}. "
            f"Add a route that ends in a traded currency or extend lookup overrides."
        )

    cost_chaos = start_amount * start_price
    revenue_chaos = amount * end_price
    profit_chaos = revenue_chaos - cost_chaos
    roi_percent = (profit_chaos / cost_chaos) * 100 if cost_chaos > 0 else 0.0

    return FlipResult(
        route_name=route_name,
        start_currency=start_currency,
        start_amount=start_amount,
        end_currency=end_currency,
        end_amount=amount,
        cost_chaos=cost_chaos,
        revenue_chaos=revenue_chaos,
        profit_chaos=profit_chaos,
        roi_percent=roi_percent,
        step_notes=step_notes,
    )


def build_price_lookup(rows: list[MarketRow]) -> dict[str, float]:
    lookup: dict[str, float] = {}
    for row in rows:
        lookup[_normalize_key(row.id)] = row.chaos_value
        lookup[_normalize_key(row.name)] = row.chaos_value
    return lookup


def parse_market_rows(payload: dict[str, Any]) -> list[MarketRow]:
    if isinstance(payload.get("markets"), list):
        return _parse_currency_exchange_rows(payload)

    name_lookup = _build_name_lookup(payload)
    chaos_per_primary = _extract_chaos_per_primary(payload)

    rows: list[MarketRow] = []
    for line in extract_lines(payload):
        row_id = str(line.get("id", "")).strip()
        if not row_id:
            continue

        name = name_lookup.get(row_id) or _extract_name(line) or _humanize_id(row_id)
        primary_value = _to_float(line.get("primaryValue"))
        if primary_value is None:
            continue

        if chaos_per_primary is not None:
            chaos_value = primary_value * chaos_per_primary
        else:
            legacy_chaos = _extract_chaos_value(line)
            if legacy_chaos is None:
                continue
            chaos_value = legacy_chaos

        rows.append(
            MarketRow(
                id=row_id,
                name=name,
                chaos_value=chaos_value,
                primary_value=primary_value,
            )
        )

    log.debug("Parsed market rows", extra={"count": len(rows)})
    return rows


def _parse_currency_exchange_rows(payload: dict[str, Any]) -> list[MarketRow]:
    markets = payload.get("markets")
    if not isinstance(markets, list):
        return []

    graph: dict[str, dict[str, float]] = {}
    for market in markets:
        if not isinstance(market, dict):
            continue
        market_pair = market.get("market_pair")
        if not isinstance(market_pair, list) or len(market_pair) != 2:
            continue
        left = market_pair[0]
        right = market_pair[1]
        if not isinstance(left, str) or not isinstance(right, str):
            continue

        ratio = market.get("lowest_ratio")
        if not isinstance(ratio, dict):
            continue
        left_qty = _to_float(ratio.get(left))
        right_qty = _to_float(ratio.get(right))
        if left_qty is None or right_qty is None or left_qty <= 0 or right_qty <= 0:
            continue

        right_per_left = right_qty / left_qty
        left_per_right = left_qty / right_qty
        graph.setdefault(left, {})[right] = right_per_left
        graph.setdefault(right, {})[left] = left_per_right

    anchor = _find_anchor_currency_id(graph)
    if anchor is None:
        return []

    chaos_values = _bfs_currency_values(graph, anchor)
    rows: list[MarketRow] = []
    for currency_id, chaos_value in chaos_values.items():
        canonical_id = _canonical_currency_id(currency_id)
        rows.append(
            MarketRow(
                id=canonical_id,
                name=_canonical_currency_name(currency_id),
                chaos_value=chaos_value,
                primary_value=chaos_value,
            )
        )
    return rows


def _find_anchor_currency_id(graph: dict[str, dict[str, float]]) -> str | None:
    if not graph:
        return None

    for candidate in graph:
        lower_candidate = candidate.lower()
        if "currencyrerollrare" in lower_candidate or lower_candidate.endswith("/chaosorb"):
            return candidate

    return next(iter(graph))


def _bfs_currency_values(graph: dict[str, dict[str, float]], anchor: str) -> dict[str, float]:
    values: dict[str, float] = {anchor: 1.0}
    queue: list[str] = [anchor]

    while queue:
        current = queue.pop(0)
        current_value = values[current]
        for neighbor, neighbor_per_current in graph.get(current, {}).items():
            if neighbor_per_current <= 0:
                continue
            neighbor_value = current_value / neighbor_per_current
            if neighbor not in values:
                values[neighbor] = neighbor_value
                queue.append(neighbor)
                continue

            # Smooth contradictory pair observations with a midpoint to reduce noise.
            values[neighbor] = (values[neighbor] + neighbor_value) / 2.0

    return values


def _canonical_currency_id(currency_id: str) -> str:
    key = currency_id.strip().split("/")[-1]
    lower = key.lower()
    aliases = {
        "currencyrerollrare": "chaos",
        "currencyreraresocketcolours": "chromatic",
        "currencyupgradetorare": "regal",
        "currencyupgradetomagic": "transmute",
        "currencyaddmodtomagic": "augmentation",
        "currencyrerollmagic": "alteration",
        "currencymodvalues": "divine",
        "currencyconverttox": "exalt",
        "currencyconverttoxpre210": "exalt",
        "currencyupgradegemquality": "gemcutter",
        "currencyidentification": "wisdom",
        "currencyportal": "portal",
    }
    return aliases.get(lower, key)


def _canonical_currency_name(currency_id: str) -> str:
    key = currency_id.strip().split("/")[-1]
    names = {
        "CurrencyRerollRare": "Chaos Orb",
        "CurrencyModValues": "Divine Orb",
        "CurrencyConvertToX": "Exalted Orb",
        "CurrencyConvertToXPre210": "Exalted Orb",
        "CurrencyIdentification": "Scroll of Wisdom",
        "CurrencyPortal": "Portal Scroll",
    }
    if key in names:
        return names[key]
    return _humanize_cx_id(key)


def _humanize_cx_id(value: str) -> str:
    parts = []
    token = value.removeprefix("Currency")
    for ch in token:
        if ch.isupper() and parts:
            parts.append(" ")
        parts.append(ch)
    return "".join(parts).strip() or value


def _extract_name(line: dict[str, Any]) -> str | None:
    for key in ("currencyTypeName", "name", "baseType"):
        value = line.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _build_name_lookup(payload: dict[str, Any]) -> dict[str, str]:
    core = payload.get("core")
    if not isinstance(core, dict):
        return {}

    items = core.get("items")
    if not isinstance(items, list):
        return {}

    lookup: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        row_id = item.get("id")
        row_name = item.get("name")
        if isinstance(row_id, str) and isinstance(row_name, str) and row_id.strip() and row_name.strip():
            lookup[row_id.strip()] = row_name.strip()
    return lookup


def _extract_chaos_per_primary(payload: dict[str, Any]) -> float | None:
    core = payload.get("core")
    if not isinstance(core, dict):
        return None

    rates = core.get("rates")
    if not isinstance(rates, dict):
        return None

    chaos_rate = _to_float(rates.get("chaos"))
    return chaos_rate


def _extract_chaos_value(line: dict[str, Any]) -> float | None:
    for key in ("chaosEquivalent", "chaosValue", "payChaosEquivalent"):
        value = _to_float(line.get(key))
        if value is not None:
            return value

    receive = line.get("receive")
    if isinstance(receive, dict):
        value = _to_float(receive.get("value"))
        if value is not None:
            return value

    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _sanitize_filename(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in lowered)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


def _humanize_id(value: str) -> str:
    return value.replace("-", " ").strip().title()


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _lookup_price(price_map: dict[str, float], currency: str) -> float | None:
    normalized = _normalize_key(currency)
    direct = price_map.get(normalized)
    if direct is not None:
        return direct

    for alias in _currency_aliases(normalized):
        value = price_map.get(alias)
        if value is not None:
            return value
    return None


def lookup_price_in_map(price_map: dict[str, float], currency: str) -> float | None:
    return _lookup_price(price_map, currency)


def resolve_currency_price(payload: dict[str, Any], currency: str) -> float | None:
    rows = parse_market_rows(payload)
    price_map = build_price_lookup(rows)
    return _lookup_price(price_map, currency)


def _currency_aliases(normalized_currency: str) -> list[str]:
    aliases: dict[str, list[str]] = {
        "exalt": ["exalted", "exalted-orb"],
        "exalted": ["exalt", "exalted-orb"],
        "exalted-orb": ["exalt", "exalted"],
        "chaos": ["chaos-orb"],
        "chaos-orb": ["chaos"],
        "div": ["divine", "divine-orb"],
        "divine": ["div", "divine-orb"],
        "divine-orb": ["divine", "div"],
    }
    return aliases.get(normalized_currency, [])


def _normalize_previous_prices(values: dict[str, float] | None) -> dict[str, float]:
    if not values:
        return {}

    normalized: dict[str, float] = {}
    for key, raw_value in values.items():
        if not isinstance(key, str):
            continue
        try:
            normalized[_normalize_key(key)] = float(raw_value)
        except (TypeError, ValueError):
            continue
    return normalized


def _build_trend_alignment(action: str, trend_1h_percent: float | None) -> str | None:
    if trend_1h_percent is None:
        return None

    if action == "buy" and trend_1h_percent < 0:
        return "aligned"
    if action == "sell" and trend_1h_percent > 0:
        return "aligned"
    if action == "hold":
        return "neutral"
    return "counter_trend"
