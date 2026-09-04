from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re

from app.adapters.market_adapter import normalize_market_rows_for_store
from app.contracts.responses import (
    ConversionView,
    CurrencyRecommendationView,
    FilterBuildResponse,
    FilterInitResponse,
    FilterListResponse,
    FlipSimulationView,
    MarketItemHistoryPointView,
    MarketItemHistoryView,
    HoldingItemView,
    HoldingsView,
    MarketRowView,
    MarketSnapshotView,
    MarketWorkflowResponse,
    TrendSignalView,
    TopEntry,
    VendorOpportunityView,
)
from app.domain.filter_profiles import build_score_profile_rules
from app.domain.market_types import (
    EXCHANGE_OVERVIEW_URL,
    MarketTypeConfig,
    MarketTypeEntry,
    STASH_ITEM_OVERVIEW_URL,
    load_market_type_config,
)
from app.domain.scoring import MarketItemScore
from app.filter_manager import FilterManager
from app.infrastructure.market_store import HoldingRecord, MarketItemStatsRecord, SQLiteMarketStore
from app.market import (
    MarketClient,
    build_currency_recommendations,
    lookup_price_in_map,
    compare_vendor_to_market,
    convert_currency_amount,
    load_flip_routes,
    load_vendor_chaos_costs,
    resolve_currency_price,
    simulate_flip_route,
    summarize_market,
)


log = logging.getLogger("poe-helper.application")
MARKET_CONFIG_PATH = "config/market_types.json"
MARKET_DB_PATH = "data/market/poe_market.db"
MAX_MARKET_SNAPSHOT_AGE = timedelta(hours=1)
POE_CDN_BASE_URL = "https://web.poecdn.com"


def _resolve_market_types(market_type: str, config: MarketTypeConfig) -> list[MarketTypeEntry]:
    normalized = market_type.strip()
    if not normalized:
        return []

    if normalized.lower() == "all":
        return [entry for entry in config.entries() if entry.category == "items" and entry.enabled]

    if "," in normalized:
        requested_types = [item.strip() for item in normalized.split(",") if item.strip()]
    else:
        requested_types = [normalized]

    resolved: list[MarketTypeEntry] = []
    seen: set[str] = set()
    for requested in requested_types:
        entry = config.find_entry(requested)
        if entry is None:
            entry = MarketTypeEntry(
                category="custom",
                name=requested,
                fetch_name=requested,
                fetch_url=EXCHANGE_OVERVIEW_URL,
                enabled=True,
            )
        if not entry.enabled:
            continue
        if entry.name in seen:
            continue
        seen.add(entry.name)
        resolved.append(entry)
    return resolved


def _snapshot_slug(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in lowered)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


def _source_scope_for_url(fetch_url: str) -> str:
    normalized = fetch_url.strip().lower()
    if normalized == EXCHANGE_OVERVIEW_URL.lower():
        return "exchange"
    if normalized == STASH_ITEM_OVERVIEW_URL.lower():
        return "stash-item"
    return _snapshot_slug(fetch_url)


def _parse_snapshot_timestamp(file_path: Path) -> datetime | None:
    match = re.search(r"_(\d{8}T\d{6}Z)\.json$", file_path.name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def _find_latest_snapshot(output_directory: str, league: str, market_type: str) -> tuple[Path, datetime] | None:
    output_dir = Path(output_directory).expanduser().resolve()
    if not output_dir.exists() or not output_dir.is_dir():
        return None

    prefix = f"{_snapshot_slug(league)}_{_snapshot_slug(market_type)}_"
    latest_path: Path | None = None
    latest_time: datetime | None = None
    for candidate in output_dir.glob(f"{prefix}*.json"):
        candidate_time = _parse_snapshot_timestamp(candidate)
        if candidate_time is None:
            continue
        if latest_time is None or candidate_time > latest_time:
            latest_time = candidate_time
            latest_path = candidate

    if latest_path is None or latest_time is None:
        return None
    return latest_path, latest_time


def initialize_filter_manager(filter_dir: str | None) -> tuple[FilterInitResponse, FilterManager | None]:
    try:
        manager = FilterManager(
            filter_directory=filter_dir,
            create_if_missing=filter_dir is None,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        return FilterInitResponse(ok=False, error=str(exc)), None

    return FilterInitResponse(ok=True, filter_directory=str(manager.filter_directory)), manager


def list_filters(manager: FilterManager) -> FilterListResponse:
    try:
        filters = manager.list_filters()
    except OSError as exc:
        return FilterListResponse(ok=False, error=str(exc), filter_directory=str(manager.filter_directory))

    return FilterListResponse(ok=True, filter_directory=str(manager.filter_directory), filters=filters)


def build_filter(manager: FilterManager, source: str | None, output: str | None, profile: str) -> FilterBuildResponse:
    if not source or not output:
        return FilterBuildResponse(ok=False, error="--build requires both --source and --output.")

    try:
        output_path = manager.create_managed_filter(source, output, profile)
    except FileNotFoundError as exc:
        return FilterBuildResponse(ok=False, error=str(exc))

    return FilterBuildResponse(ok=True, output_path=str(output_path))


def build_score_profile_filter(
    manager: FilterManager,
    *,
    source: str | None,
    output: str | None,
    scores: list[MarketItemScore],
) -> FilterBuildResponse:
    if not source or not output:
        return FilterBuildResponse(ok=False, error="--build requires both --source and --output.")

    try:
        base_text = manager.read_filter(source)
    except FileNotFoundError as exc:
        return FilterBuildResponse(ok=False, error=str(exc))

    profile_rules = build_score_profile_rules(scores)
    merged_text = manager.merge_filter_with_rules(base_text, profile_rules, "score")
    try:
        output_path = manager.write_filter(output, merged_text)
    except OSError as exc:
        return FilterBuildResponse(ok=False, error=str(exc))

    return FilterBuildResponse(ok=True, output_path=str(output_path))


def analyze_currency_recommendations(
    payload: dict,
    *,
    market_type: str,
    source_currency: str,
    amount: float,
    previous_prices: dict[str, float] | None = None,
    holdings: dict[str, float] | None = None,
    trend_signals: dict[str, dict[str, float | str | None]] | None = None,
    min_change_percent: float = 0.5,
    min_trade_units: float = 1.0,
    source_price_override: float | None = None,
    previous_source_price_override: float | None = None,
    divine_price_override: float | None = None,
    exalt_price_override: float | None = None,
    max_results: int = 5,
) -> list[CurrencyRecommendationView]:
    recommendations = build_currency_recommendations(
        payload,
        market_type=market_type,
        source_currency=source_currency,
        amount=amount,
        previous_prices=previous_prices,
        holdings=holdings,
        trend_signals=trend_signals,
        min_change_percent=min_change_percent,
        min_trade_units=min_trade_units,
        source_price_override=source_price_override,
        previous_source_price_override=previous_source_price_override,
        divine_price_override=divine_price_override,
        exalt_price_override=exalt_price_override,
        max_results=max_results,
    )
    return [
        CurrencyRecommendationView(
            market_type=item["market_type"],
            source_currency=item["source_currency"],
            target_currency=item["target_currency"],
            target_name=item["target_name"],
            amount=item["amount"],
            converted_amount=item["converted_amount"],
            value_chaos=item["value_chaos"],
            value_divine=item["value_divine"],
            spent_source_units=item["spent_source_units"],
            leftover_source_units=item["leftover_source_units"],
            action=item["action"],
            current_ratio=item["current_ratio"],
            previous_ratio=item["previous_ratio"],
            ratio_change_percent=item["ratio_change_percent"],
            affordable_units=item["affordable_units"],
            whole_units_affordable=item["whole_units_affordable"],
            is_affordable=item["is_affordable"],
            owned_target_units=item["owned_target_units"],
            whole_units_owned=item["whole_units_owned"],
            can_sell=item["can_sell"],
            actionable_action=item["actionable_action"],
            trend_1h_percent=item["trend_1h_percent"],
            trend_2h_percent=item["trend_2h_percent"],
            trend_12h_percent=item["trend_12h_percent"],
            trend_24h_percent=item["trend_24h_percent"],
            short_term_reversal=item["short_term_reversal"],
            trend_alignment=item["trend_alignment"],
            value_exalt=item["value_exalt"],
        )
        for item in recommendations
    ]


def _build_trend_signal_lookup(stats_rows: list[MarketItemStatsRecord]) -> dict[str, dict[str, float | str | None]]:
    lookup: dict[str, dict[str, float | str | None]] = {}
    for row in stats_rows:
        signal = {
            "trend_1h_percent": row.trend_1h_percent,
            "trend_2h_percent": row.trend_2h_percent,
            "trend_12h_percent": row.trend_12h_percent,
            "trend_24h_percent": row.trend_24h_percent,
            "short_term_reversal": row.short_term_reversal,
        }
        lookup[row.item_id] = signal
        lookup[row.item_name] = signal
    return lookup


def _build_reversal_highlights(
    stats_rows: list[MarketItemStatsRecord],
    *,
    market_type: str,
    limit: int = 10,
) -> list[TrendSignalView]:
    candidates = [
        row
        for row in stats_rows
        if row.short_term_reversal in {"bearish_reversal", "bullish_reversal"}
    ]
    candidates.sort(
        key=lambda row: (
            abs(row.trend_1h_percent) if row.trend_1h_percent is not None else 0.0,
            abs(row.trend_2h_percent) if row.trend_2h_percent is not None else 0.0,
        ),
        reverse=True,
    )
    top = candidates[: max(1, limit)]

    return [
        TrendSignalView(
            market_type=market_type,
            target_currency=row.item_id,
            target_name=row.item_name,
            short_term_reversal=row.short_term_reversal,
            trend_1h_percent=row.trend_1h_percent,
            trend_2h_percent=row.trend_2h_percent,
            trend_12h_percent=row.trend_12h_percent,
            trend_24h_percent=row.trend_24h_percent,
            latest_chaos_value=row.latest_chaos_value,
        )
        for row in top
    ]


def _resolve_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
    if image_path.startswith("/"):
        return f"{POE_CDN_BASE_URL}{image_path}"
    return f"{POE_CDN_BASE_URL}/{image_path.lstrip('/')}"


def read_market_snapshot(
    *,
    league: str,
    market_type: str,
    db_path: str = MARKET_DB_PATH,
    limit: int = 10,
) -> MarketSnapshotView:
    with SQLiteMarketStore(db_path=db_path) as store:
        latest_rows = store.get_latest_market_rows(league, market_type)
        if not latest_rows:
            return MarketSnapshotView(
                ok=False,
                league=league,
                market_type=market_type,
                error="No market rows found for the requested league and market type.",
            )

        stats_rows = store.get_market_item_stats(league, market_type)
        latest_fetched_at = max(row.fetched_at for row in latest_rows).isoformat()
        ordered_rows = sorted(latest_rows, key=lambda row: row.chaos_value, reverse=True)
        top_entries = [TopEntry(name=row.item_name, chaos_value=row.chaos_value) for row in ordered_rows[: max(1, limit)]]
        trend_highlights = _build_reversal_highlights(stats_rows, market_type=market_type, limit=limit)

        return MarketSnapshotView(
            ok=True,
            league=league,
            market_type=market_type,
            latest_fetched_at=latest_fetched_at,
            item_count=len(latest_rows),
            top_entries=top_entries,
            rows=[
                MarketRowView(
                    league=row.league,
                    market_type=row.market_type,
                    item_id=row.item_id,
                    item_name=row.item_name,
                    icon_url=_resolve_image_url(row.image_path),
                    chaos_value=row.chaos_value,
                    primary_value=row.primary_value,
                    fetched_at=row.fetched_at.isoformat(),
                    vendor_value=row.vendor_value,
                )
                for row in latest_rows
            ],
            trend_highlights=trend_highlights,
        )


def read_market_item_history(
    *,
    league: str,
    market_type: str,
    item_id: str,
    db_path: str = MARKET_DB_PATH,
) -> MarketItemHistoryView:
    with SQLiteMarketStore(db_path=db_path) as store:
        history_rows = store.get_item_history(league, market_type, item_id)
        if not history_rows:
            return MarketItemHistoryView(
                ok=False,
                league=league,
                market_type=market_type,
                item_id=item_id,
                error="No history found for the requested item.",
            )

        latest_row = history_rows[-1]
        return MarketItemHistoryView(
            ok=True,
            league=league,
            market_type=market_type,
            item_id=item_id,
            item_name=latest_row.item_name,
            icon_url=_resolve_image_url(latest_row.image_path),
            points=[
                MarketItemHistoryPointView(
                    fetched_at=row.fetched_at.isoformat(),
                    chaos_value=row.chaos_value,
                    primary_value=row.primary_value,
                    vendor_value=row.vendor_value,
                )
                for row in history_rows
            ],
        )


def read_market_types(config_path: str = MARKET_CONFIG_PATH) -> list[str]:
    config = load_market_type_config(config_path)
    return [item for item in config.all_types if item not in config.disabled_types]


def _parse_non_negative_float(value: object) -> float | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount < 0:
        return None
    return amount


def _build_holdings_map_from_store(store: SQLiteMarketStore, league: str, market_types: list[MarketTypeEntry]) -> dict[str, float]:
    if not hasattr(store, "get_holdings"):
        return {}

    merged: dict[str, float] = {}
    for scope_type in market_types:
        for row in store.get_holdings(league, scope_type.name):
            if row.amount <= 0:
                continue
            merged[row.item_id] = merged.get(row.item_id, 0.0) + row.amount
            merged[row.item_name] = merged.get(row.item_name, 0.0) + row.amount
    return merged


def read_holdings(*, league: str, market_type: str, db_path: str = MARKET_DB_PATH) -> HoldingsView:
    with SQLiteMarketStore(db_path=db_path) as store:
        items_with_stats = store.get_market_item_holdings(league, market_type)
        if items_with_stats:
            return HoldingsView(
                ok=True,
                league=league,
                market_type=market_type,
                items=[
                    HoldingItemView(
                        league=row.league,
                        market_type=row.market_type,
                        item_id=row.item_id,
                        item_name=row.item_name,
                        amount=row.amount,
                        latest_chaos_value=row.latest_chaos_value,
                        icon_url=_resolve_image_url(row.image_path),
                        updated_at=row.updated_at.isoformat() if row.updated_at is not None else None,
                    )
                    for row in items_with_stats
                ],
            )

        plain_holdings = store.get_holdings(league, market_type)
        return HoldingsView(
            ok=True,
            league=league,
            market_type=market_type,
            items=[
                HoldingItemView(
                    league=row.league,
                    market_type=row.market_type,
                    item_id=row.item_id,
                    item_name=row.item_name,
                    amount=row.amount,
                    latest_chaos_value=None,
                    icon_url=None,
                    updated_at=row.updated_at.isoformat(),
                )
                for row in plain_holdings
            ],
        )


def save_holdings(
    *,
    league: str,
    market_type: str,
    items: list[dict[str, object]],
    db_path: str = MARKET_DB_PATH,
) -> HoldingsView:
    now = datetime.now(UTC).replace(microsecond=0)
    parsed: list[HoldingRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id", "")).strip()
        item_name = str(item.get("item_name", "")).strip()
        amount = _parse_non_negative_float(item.get("amount"))
        if not item_id or not item_name or amount is None:
            continue
        parsed.append(
            HoldingRecord(
                league=league,
                market_type=market_type,
                item_id=item_id,
                item_name=item_name,
                amount=amount,
                updated_at=now,
            )
        )

    if not parsed:
        return HoldingsView(
            ok=False,
            league=league,
            market_type=market_type,
            error="No valid holdings items were provided.",
        )

    with SQLiteMarketStore(db_path=db_path) as store:
        store.upsert_holdings(parsed)

    return read_holdings(league=league, market_type=market_type, db_path=db_path)


def execute_market_workflow(
    *,
    league: str,
    market_type: str,
    market_out_dir: str,
    market_limit: int,
    vendor_file: str | None,
    min_margin: float,
    convert: bool,
    from_currency: str | None,
    to_currency: str | None,
    amount: float,
    flip_route_file: str | None,
    flip_route_name: str | None,
    recommend: bool = False,
    source_currency: str | None = None,
    recommend_min_change: float = 0.5,
    recommend_min_units: float = 1.0,
) -> MarketWorkflowResponse:
    config = load_market_type_config(MARKET_CONFIG_PATH)
    resolved_types = _resolve_market_types(market_type, config)
    if not resolved_types:
        return MarketWorkflowResponse(ok=False, error="No market types were requested.", error_stage="fetch")

    top_entries: list[TopEntry] = []
    primary_payload: dict | None = None
    primary_snapshot_path: str | None = None
    previous_prices: dict[str, float] = {}
    previous_prices_by_type: dict[str, dict[str, float]] = {}
    payload_by_type: dict[str, dict] = {}
    trend_lookup_by_type: dict[str, dict[str, dict[str, float | str | None]]] = {}
    holdings: dict[str, float] | None = None
    trend_highlights: list[TrendSignalView] = []
    market_data_fetched_at: str | None = None
    market_data_source: str | None = None

    with SQLiteMarketStore(db_path=MARKET_DB_PATH) as store:
        store.sync_market_types(config)

        for configured_entry in resolved_types:
            configured_display_type = configured_entry.name
            configured_fetch_type = configured_entry.fetch_name
            configured_fetch_url = configured_entry.fetch_url
            snapshot_cache_key = f"{configured_fetch_type}_{_source_scope_for_url(configured_fetch_url)}"
            try:
                client = MarketClient()
                client.base_url = configured_fetch_url
                latest_snapshot = _find_latest_snapshot(market_out_dir, league, snapshot_cache_key)
                now_utc = datetime.now(UTC)
                use_cached_snapshot = False
                payload: dict
                snapshot_path: Path

                if latest_snapshot is not None:
                    snapshot_candidate, fetched_at = latest_snapshot
                    if now_utc - fetched_at <= MAX_MARKET_SNAPSHOT_AGE:
                        payload = json.loads(snapshot_candidate.read_text(encoding="utf-8"))
                        snapshot_path = snapshot_candidate
                        use_cached_snapshot = True
                    else:
                        payload = client.fetch_overview(league, configured_fetch_type)
                        snapshot_path = client.save_snapshot(payload, market_out_dir, league, snapshot_cache_key)
                else:
                    payload = client.fetch_overview(league, configured_fetch_type)
                    snapshot_path = client.save_snapshot(payload, market_out_dir, league, snapshot_cache_key)

                latest_rows = store.get_latest_market_rows(league, configured_display_type)
                if latest_rows:
                    previous_prices = {row.item_id: row.chaos_value for row in latest_rows}
                    previous_prices_by_type[configured_display_type] = previous_prices
                else:
                    previous_prices_by_type[configured_display_type] = {}

                payload_by_type[configured_display_type] = payload

                needs_row_refresh = not latest_rows or not use_cached_snapshot or any(row.image_path is None for row in latest_rows)
                if needs_row_refresh:
                    rows = normalize_market_rows_for_store(
                        payload,
                        league=league,
                        market_type=configured_display_type,
                        fetched_at=datetime.now(),
                    )
                    store.save_market_rows(rows)

                store.refresh_market_item_stats(league, configured_display_type)
                stats_rows = store.get_market_item_stats(league, configured_display_type)
                trend_lookup_by_type[configured_display_type] = _build_trend_signal_lookup(stats_rows)

                if configured_display_type.lower() == "currency":
                    trend_highlights = _build_reversal_highlights(
                        stats_rows,
                        market_type=configured_display_type,
                        limit=market_limit,
                    )

                if primary_payload is None:
                    primary_payload = payload
                    primary_snapshot_path = str(snapshot_path)
                    snapshot_time = _parse_snapshot_timestamp(snapshot_path)
                    market_data_fetched_at = snapshot_time.isoformat() if snapshot_time is not None else None
                    market_data_source = "cache" if use_cached_snapshot else "refetch"

                top_entries.extend(
                    TopEntry(name=name, chaos_value=chaos_value)
                    for name, chaos_value in summarize_market(payload, limit=market_limit)
                )
            except Exception as exc:  # pragma: no cover - network/runtime errors
                log.exception("Market fetch failed for configured type %s", configured_display_type)
                return MarketWorkflowResponse(
                    ok=False,
                    error=f"Market fetch failed for {configured_display_type}: {exc}",
                    error_stage="fetch",
                )

        holdings = _build_holdings_map_from_store(store, league, resolved_types)

    if primary_payload is None:
        return MarketWorkflowResponse(ok=False, error="No market payloads were fetched.", error_stage="fetch")

    response = MarketWorkflowResponse(
        ok=True,
        snapshot_path=primary_snapshot_path,
        market_data_fetched_at=market_data_fetched_at,
        market_data_source=market_data_source,
        top_entries=top_entries,
    )
    response.trend_highlights = trend_highlights

    if vendor_file:
        try:
            vendor_costs = load_vendor_chaos_costs(vendor_file)
        except Exception as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Vendor file load failed: {exc}",
                error_stage="vendor",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
            )

        opportunities = compare_vendor_to_market(primary_payload, vendor_costs, min_margin_chaos=min_margin)
        response.vendor_opportunities = [
            VendorOpportunityView(
                name=row.name,
                market_chaos_value=row.market_chaos_value,
                vendor_chaos_cost=row.vendor_chaos_cost,
                margin_chaos=row.margin_chaos,
            )
            for row in opportunities
        ]
        if not response.vendor_opportunities:
            response.vendor_no_opportunities = True
            return response

    if convert:
        if not from_currency or not to_currency:
            return MarketWorkflowResponse(
                ok=False,
                error="--convert requires --from-currency and --to-currency.",
                error_stage="convert",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
            )
        try:
            converted = convert_currency_amount(
                primary_payload,
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
            )
        except ValueError as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Conversion failed: {exc}",
                error_stage="convert",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
            )

        response.conversion = ConversionView(
            from_currency=from_currency,
            to_currency=to_currency,
            amount=amount,
            converted_amount=converted,
        )

    if recommend:
        source_currency = source_currency or "exalt"
        display_types = [entry.name for entry in resolved_types]
        currency_type = next((item for item in display_types if item.lower() == "currency"), display_types[0])
        reference_payload = payload_by_type.get(currency_type, primary_payload)
        reference_previous_prices = previous_prices_by_type.get(currency_type, {})
        source_price_override = resolve_currency_price(reference_payload, source_currency) if reference_payload else None
        divine_price_override = resolve_currency_price(reference_payload, "divine") if reference_payload else None
        exalt_price_override = resolve_currency_price(reference_payload, "exalt") if reference_payload else None
        previous_source_price_override = lookup_price_in_map(reference_previous_prices, source_currency)

        all_recommendations: list[CurrencyRecommendationView] = []
        recommendation_errors: list[str] = []
        for configured_type in display_types:
            payload = payload_by_type.get(configured_type)
            if payload is None:
                continue
            try:
                type_recommendations = analyze_currency_recommendations(
                    payload,
                    market_type=configured_type,
                    source_currency=source_currency,
                    amount=amount,
                    previous_prices=previous_prices_by_type.get(configured_type, {}),
                    holdings=holdings,
                    trend_signals=trend_lookup_by_type.get(configured_type, {}),
                    min_change_percent=recommend_min_change,
                    min_trade_units=recommend_min_units,
                    source_price_override=source_price_override,
                    previous_source_price_override=previous_source_price_override,
                    divine_price_override=divine_price_override,
                    exalt_price_override=exalt_price_override,
                    max_results=market_limit,
                )
                all_recommendations.extend(type_recommendations)
            except ValueError as exc:
                recommendation_errors.append(f"{configured_type}: {exc}")

        if not all_recommendations:
            return MarketWorkflowResponse(
                ok=False,
                error="Recommendation failed: " + "; ".join(recommendation_errors or ["no recommendation candidates"]),
                error_stage="recommend",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
                conversion=response.conversion,
            )

        all_recommendations.sort(
            key=lambda rec: (
                abs(rec.ratio_change_percent) if rec.ratio_change_percent is not None else 0.0,
                rec.converted_amount,
            ),
            reverse=True,
        )
        response.recommendations = all_recommendations[: max(1, market_limit)]

    if flip_route_file or flip_route_name:
        if not flip_route_file or not flip_route_name:
            return MarketWorkflowResponse(
                ok=False,
                error="Flip simulation requires both --flip-route-file and --flip-route-name.",
                error_stage="flip",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
                conversion=response.conversion,
            )

        try:
            routes = load_flip_routes(flip_route_file)
        except Exception as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Route file load failed: {exc}",
                error_stage="flip",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
                conversion=response.conversion,
            )

        steps = routes.get(flip_route_name)
        if not steps:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Route not found: {flip_route_name}",
                error_stage="flip",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
                conversion=response.conversion,
                available_routes=sorted(routes.keys()),
            )

        try:
            result = simulate_flip_route(
                primary_payload,
                route_name=flip_route_name,
                steps=steps,
                start_amount=amount,
            )
        except ValueError as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Flip simulation failed: {exc}",
                error_stage="flip",
                snapshot_path=primary_snapshot_path,
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
                conversion=response.conversion,
            )

        response.flip_simulation = FlipSimulationView(
            route_name=result.route_name,
            start_currency=result.start_currency,
            start_amount=result.start_amount,
            end_currency=result.end_currency,
            end_amount=result.end_amount,
            cost_chaos=result.cost_chaos,
            revenue_chaos=result.revenue_chaos,
            profit_chaos=result.profit_chaos,
            roi_percent=result.roi_percent,
            step_notes=result.step_notes,
        )

    return response
