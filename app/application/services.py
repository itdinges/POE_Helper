from __future__ import annotations

import logging

from app.contracts.responses import (
    ConversionView,
    FilterBuildResponse,
    FilterInitResponse,
    FilterListResponse,
    FlipSimulationView,
    MarketWorkflowResponse,
    TopEntry,
    VendorOpportunityView,
)
from app.domain.filter_profiles import build_score_profile_rules
from app.domain.scoring import MarketItemScore
from app.filter_manager import FilterManager
from app.market import (
    MarketClient,
    compare_vendor_to_market,
    convert_currency_amount,
    load_flip_routes,
    load_vendor_chaos_costs,
    simulate_flip_route,
    summarize_market,
)


log = logging.getLogger("poe-helper.application")


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
) -> MarketWorkflowResponse:
    client = MarketClient()
    try:
        payload = client.fetch_overview(league, market_type)
    except Exception as exc:  # pragma: no cover - network/runtime errors
        log.exception("Market fetch failed")
        return MarketWorkflowResponse(ok=False, error=f"Market fetch failed: {exc}", error_stage="fetch")

    snapshot_path = client.save_snapshot(payload, market_out_dir, league, market_type)

    top_entries = [TopEntry(name=name, chaos_value=chaos_value) for name, chaos_value in summarize_market(payload, limit=market_limit)]
    if not top_entries:
        return MarketWorkflowResponse(
            ok=True,
            snapshot_path=str(snapshot_path),
            top_entries=[],
        )

    response = MarketWorkflowResponse(
        ok=True,
        snapshot_path=str(snapshot_path),
        top_entries=top_entries,
    )

    if vendor_file:
        try:
            vendor_costs = load_vendor_chaos_costs(vendor_file)
        except Exception as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Vendor file load failed: {exc}",
                error_stage="vendor",
                snapshot_path=str(snapshot_path),
                top_entries=top_entries,
            )

        opportunities = compare_vendor_to_market(payload, vendor_costs, min_margin_chaos=min_margin)
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
                snapshot_path=str(snapshot_path),
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
            )
        try:
            converted = convert_currency_amount(
                payload,
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
            )
        except ValueError as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Conversion failed: {exc}",
                error_stage="convert",
                snapshot_path=str(snapshot_path),
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

    if flip_route_file or flip_route_name:
        if not flip_route_file or not flip_route_name:
            return MarketWorkflowResponse(
                ok=False,
                error="Flip simulation requires both --flip-route-file and --flip-route-name.",
                error_stage="flip",
                snapshot_path=str(snapshot_path),
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
                snapshot_path=str(snapshot_path),
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
                snapshot_path=str(snapshot_path),
                top_entries=top_entries,
                vendor_opportunities=response.vendor_opportunities,
                vendor_no_opportunities=response.vendor_no_opportunities,
                conversion=response.conversion,
                available_routes=sorted(routes.keys()),
            )

        try:
            result = simulate_flip_route(
                payload,
                route_name=flip_route_name,
                steps=steps,
                start_amount=amount,
            )
        except ValueError as exc:
            return MarketWorkflowResponse(
                ok=False,
                error=f"Flip simulation failed: {exc}",
                error_stage="flip",
                snapshot_path=str(snapshot_path),
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
