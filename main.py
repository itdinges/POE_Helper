from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.application.services import build_filter, execute_market_workflow, initialize_filter_manager, list_filters
from app.observability import configure_logging, tail_log_file


log = logging.getLogger("poe-helper")
SETTINGS_PATH = Path("config/settings.json")
DEFAULT_LEAGUE = "Runes of Aldur"
POE_APPS_URL = "https://www.pathofexile.com/my-account/applications"
POE_AUTHORIZE_URL = "https://www.pathofexile.com/oauth/authorize"


def _format_dutch_number(value: float, decimals: int = 3) -> str:
    formatted = format(value, f",.{decimals}f")
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _format_dutch_amount(value: float, decimals: int = 3) -> str:
    return _format_dutch_number(value, decimals)


def _print_text_table(headers: list[str], rows: list[list[str]]) -> None:
    if not headers:
        return

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def _render_row(cells: list[str]) -> str:
        return " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells))

    divider = "-+-".join("-" * width for width in widths)

    print(_render_row(headers))
    print(divider)
    for row in rows:
        print(_render_row(row))


def _trend_value(value: float | None, *, default: float) -> float:
    if value is None:
        return default
    return value


def _is_bullish_reversal_candidate(trend_1h: float | None, trend_2h: float | None, trend_24h: float | None) -> bool:
    if trend_1h is None or trend_2h is None or trend_24h is None:
        return False
    return trend_24h < 0 and trend_1h > 0 and trend_2h > 0


def _is_pullback_in_uptrend(trend_1h: float | None, trend_24h: float | None) -> bool:
    if trend_1h is None or trend_24h is None:
        return False
    return trend_24h > 0 and trend_1h < 0


def _is_risky_free_fall(trend_1h: float | None, trend_12h: float | None, trend_24h: float | None) -> bool:
    if trend_24h is None:
        return False

    sustained_drop = trend_24h <= -30.0
    short_term_drop = (
        (trend_1h is not None and trend_1h < 0)
        or (trend_12h is not None and trend_12h < 0)
    )
    return sustained_drop and short_term_drop


def _load_configured_league() -> str:
    raw = _load_settings_json()
    if not isinstance(raw, dict):
        return DEFAULT_LEAGUE

    league = raw.get("league")
    if isinstance(league, str) and league.strip():
        return league.strip()
    return DEFAULT_LEAGUE


def _load_settings_json() -> dict:
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.warning("Settings file not found, using default league", extra={"path": str(SETTINGS_PATH)})
        return {}
    except (OSError, json.JSONDecodeError):
        log.warning("Settings file unreadable, using default league", extra={"path": str(SETTINGS_PATH)})
        return {}

    if not isinstance(raw, dict):
        return {}
    return raw


def _mask_secret(value: str) -> str:
    if not value:
        return "missing"
    if len(value) <= 6:
        return "set"
    return f"set ({value[:3]}...{value[-3:]})"


def _print_oauth_setup_guide() -> None:
    settings = _load_settings_json()
    oauth = settings.get("oauth") if isinstance(settings.get("oauth"), dict) else {}

    client_id = str(oauth.get("client_id") or "").strip()
    client_secret = str(oauth.get("client_secret") or "").strip()
    realm = str(oauth.get("realm") or "poe2").strip() or "poe2"

    print("OAuth Currency Exchange setup guide")
    print("===================================")
    print("")
    print("Status from config/settings.json:")
    print(f"- oauth.client_id: {_mask_secret(client_id)}")
    print(f"- oauth.client_secret: {_mask_secret(client_secret)}")
    print(f"- oauth.realm: {realm}")
    print("")
    print("Required flow for this project (service:cxapi):")
    print("1. Open your PoE account applications page and create/manage your OAuth app:")
    print(f"   {POE_APPS_URL}")
    print("2. Use a confidential client and copy client id + client secret into config/settings.json")
    print("3. Ensure the app has access for service:cxapi")
    print("4. Run the market command with oauth source:")
    print("   python main.py --market --market-source oauth_cx --market-type Currency")
    print("")
    print("Note:")
    print("- /oauth/authorize is the user-consent page and is useful for authorization-code flows.")
    print("- The current Currency Exchange service integration here uses /oauth/token with client_credentials.")
    print(f"- Authorization page URL: {POE_AUTHORIZE_URL}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="POE 2 helper for local filter management.")
    parser.add_argument("--list", action="store_true", help="List available filter files")
    parser.add_argument("--build", action="store_true", help="Build a managed filter from a source filter")
    parser.add_argument("--source", type=str, help="Source filter filename inside OnlineFilters")
    parser.add_argument("--output", type=str, help="Output filter filename inside OnlineFilters")
    parser.add_argument(
        "--dir",
        type=str,
        dest="filter_dir",
        default=None,
        help="Optional local directory to use instead of the default POE2 OnlineFilters path",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="mapping",
        choices=["mapping", "crafting", "league_start"],
        help="Rule profile to append in managed section",
    )
    parser.add_argument("--market", action="store_true", help="Fetch poe.ninja exchange data")
    parser.add_argument(
        "--league",
        type=str,
        default="Runes of Aldur",
        help="POE2 league name for market fetch",
    )
    parser.add_argument(
        "--market-type",
        type=str,
        default="Currency",
        help="poe.ninja market type, 'all', or a comma-separated list such as Currency,Fragments",
    )
    parser.add_argument(
        "--market-source",
        type=str,
        default="poe_ninja",
        choices=["poe_ninja", "oauth_cx"],
        help="Market source for Currency (default: poe_ninja, optional: oauth_cx)",
    )
    parser.add_argument(
        "--market-out-dir",
        type=str,
        default="data/market",
        help="Directory where raw market snapshots are stored",
    )
    parser.add_argument(
        "--market-limit",
        type=int,
        default=10,
        help="How many top market rows to print",
    )
    parser.add_argument(
        "--vendor-file",
        type=str,
        default=None,
        help="Optional JSON file with vendor chaos costs for comparison",
    )
    parser.add_argument(
        "--min-margin",
        type=float,
        default=0.0,
        help="Minimum chaos margin to show in vendor comparison",
    )
    parser.add_argument("--convert", action="store_true", help="Convert currency amount using market chaos-equivalent rates")
    parser.add_argument("--recommend", action="store_true", help="Rank alternative currency conversions and show final Divine-equivalent value")
    parser.add_argument(
        "--recommend-min-change",
        type=float,
        default=0.5,
        help="Minimum ratio change percent before recommendation becomes buy/sell",
    )
    parser.add_argument(
        "--recommend-min-units",
        type=float,
        default=1.0,
        help="Minimum target units to treat a buy recommendation as actionable",
    )
    parser.add_argument(
        "--holdings-file",
        type=str,
        default=None,
        help="Optional JSON holdings file: plain map or stash-style payload with items[]",
    )
    parser.add_argument("--from-currency", type=str, default=None, help="Source currency id or name")
    parser.add_argument(
        "--source-currency",
        type=str,
        default="exalt",
        help="Source currency for recommendation ranking (default: exalt)",
    )
    parser.add_argument("--to-currency", type=str, default=None, help="Target currency id or name")
    parser.add_argument("--amount", type=float, default=1.0, help="Amount for conversion, recommendation, or route simulation")
    parser.add_argument(
        "--flip-route-file",
        type=str,
        default=None,
        help="Optional JSON file with multi-step vendor route definitions",
    )
    parser.add_argument(
        "--flip-route-name",
        type=str,
        default=None,
        help="Name of route to evaluate from the route file",
    )
    parser.add_argument("--tail-logs", action="store_true", help="Print recent backend logs")
    parser.add_argument("--follow-logs", action="store_true", help="Stream backend logs continuously")
    parser.add_argument("--oauth-setup", action="store_true", help="Print OAuth setup steps for Currency Exchange source")
    parser.add_argument("--log-lines", type=int, default=40, help="Number of log lines to show for --tail-logs")
    parser.add_argument("--log-level", type=str, default="INFO", help="Log level: DEBUG, INFO, WARNING, ERROR")
    parser.add_argument(
        "--log-file",
        type=str,
        default="data/logs/poe_helper.log",
        help="File path for backend log output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_file_path = configure_logging(log_level=args.log_level, log_file=args.log_file)
    log.info("Command started")
    configured_league = _load_configured_league()

    if args.oauth_setup:
        _print_oauth_setup_guide()
        return

    if args.tail_logs or args.follow_logs:
        log.info("Log tail requested")
        tail_log_file(str(log_file_path), lines=args.log_lines, follow=args.follow_logs)
        return

    if args.market:
        log.info("Market workflow started", extra={"league": configured_league, "market_type": args.market_type})
        response = execute_market_workflow(
            league=configured_league,
            market_type=args.market_type,
            market_out_dir=args.market_out_dir,
            market_limit=args.market_limit,
            vendor_file=args.vendor_file,
            min_margin=args.min_margin,
            convert=args.convert,
            from_currency=args.from_currency,
            to_currency=args.to_currency,
            amount=args.amount,
            flip_route_file=args.flip_route_file,
            flip_route_name=args.flip_route_name,
            recommend=args.recommend,
            source_currency=args.source_currency or args.from_currency,
            recommend_min_change=args.recommend_min_change,
            recommend_min_units=args.recommend_min_units,
            holdings_file=args.holdings_file,
            market_source=args.market_source,
        )
        if not response.ok and response.error and response.error_stage == "fetch":
            print(response.error)
            return

        if args.recommend:
            if not response.ok and response.error and response.error_stage == "recommend":
                print(response.error)
                return

            source_currency = args.source_currency or args.from_currency or "exalt"
            fetched_at = response.market_data_fetched_at or "unknown"
            source_label = response.market_data_source or "unknown"
            print(f"Market data: {source_label} | fetched_at={fetched_at}")
            print()

            if not response.recommendations:
                print("No recommendation opportunities found for the selected source currency.")
                return

            sell_candidates = [
                rec
                for rec in response.recommendations
                if rec.whole_units_owned > 0
                and (
                    rec.actionable_action == "sell"
                    or _trend_value(rec.trend_1h_percent, default=0.0) > 0
                    or _trend_value(rec.trend_12h_percent, default=0.0) > 0
                    or _trend_value(rec.trend_24h_percent, default=0.0) > 0
                )
            ]
            buy_candidates = [
                rec
                for rec in response.recommendations
                if rec.whole_units_affordable > 0
                and (
                    rec.actionable_action == "buy"
                    or rec.short_term_reversal == "bullish_reversal"
                    or _is_bullish_reversal_candidate(
                        rec.trend_1h_percent,
                        rec.trend_2h_percent,
                        rec.trend_24h_percent,
                    )
                    or _is_pullback_in_uptrend(rec.trend_1h_percent, rec.trend_24h_percent)
                )
            ]
            risky_dip_watchlist = [
                rec
                for rec in response.recommendations
                if _is_risky_free_fall(
                    rec.trend_1h_percent,
                    rec.trend_12h_percent,
                    rec.trend_24h_percent,
                )
                and rec.short_term_reversal != "bullish_reversal"
            ]

            sell_candidates.sort(
                key=lambda rec: (
                    _trend_value(rec.trend_1h_percent, default=float("-inf")),
                    _trend_value(rec.trend_12h_percent, default=float("-inf")),
                    _trend_value(rec.trend_24h_percent, default=float("-inf")),
                    _trend_value(rec.ratio_change_percent, default=float("-inf")),
                ),
                reverse=True,
            )
            buy_candidates.sort(
                key=lambda rec: (
                    _trend_value(rec.trend_1h_percent, default=float("inf")),
                    _trend_value(rec.trend_12h_percent, default=float("inf")),
                    _trend_value(rec.trend_24h_percent, default=float("inf")),
                    _trend_value(rec.ratio_change_percent, default=float("inf")),
                ),
            )
            risky_dip_watchlist.sort(
                key=lambda rec: (
                    _trend_value(rec.trend_24h_percent, default=0.0),
                    _trend_value(rec.trend_12h_percent, default=0.0),
                    _trend_value(rec.trend_1h_percent, default=0.0),
                ),
            )

            print("Sell candidates (trend + owned inventory):")
            if not sell_candidates:
                print("No sell candidates with current holdings.")
                print()
            else:
                sell_headers = [
                    "Type",
                    "Currency",
                    "Owned",
                    "1h",
                    "12h",
                    "24h",
                    "Ratio Delta",
                    "Reason",
                    "Signal",
                ]
                sell_rows = [
                    [
                        rec.market_type,
                        rec.target_name,
                        str(rec.whole_units_owned),
                        f"{_format_dutch_number(rec.trend_1h_percent, 2)}%" if rec.trend_1h_percent is not None else "n/a",
                        f"{_format_dutch_number(rec.trend_12h_percent, 2)}%" if rec.trend_12h_percent is not None else "n/a",
                        f"{_format_dutch_number(rec.trend_24h_percent, 2)}%" if rec.trend_24h_percent is not None else "n/a",
                        f"{_format_dutch_number(rec.ratio_change_percent, 2)}%" if rec.ratio_change_percent is not None else "n/a",
                        "sell" if rec.actionable_action == "sell" else "watch_trend",
                        rec.short_term_reversal or "none",
                    ]
                    for rec in sell_candidates[: args.market_limit]
                ]
                _print_text_table(sell_headers, sell_rows)
                print("Note: reason=watch_trend means trend setup only, not a strong sell signal yet.")
                print()

            print(f"Buy candidates (trend + what you can buy with {source_currency}):")
            if not buy_candidates:
                print("No buy candidates for current budget.")
                print()
            else:
                buy_headers = [
                    "Type",
                    "Currency",
                    "Can Buy",
                    f"Spend ({source_currency})",
                    f"Left ({source_currency})",
                    "1h",
                    "12h",
                    "24h",
                    "Ratio Delta",
                    "Reason",
                    "Signal",
                ]
                buy_rows = [
                    [
                        rec.market_type,
                        rec.target_name,
                        str(rec.whole_units_affordable),
                        _format_dutch_amount(rec.spent_source_units),
                        _format_dutch_amount(rec.leftover_source_units),
                        f"{_format_dutch_number(rec.trend_1h_percent, 2)}%" if rec.trend_1h_percent is not None else "n/a",
                        f"{_format_dutch_number(rec.trend_12h_percent, 2)}%" if rec.trend_12h_percent is not None else "n/a",
                        f"{_format_dutch_number(rec.trend_24h_percent, 2)}%" if rec.trend_24h_percent is not None else "n/a",
                        f"{_format_dutch_number(rec.ratio_change_percent, 2)}%" if rec.ratio_change_percent is not None else "n/a",
                        "buy" if rec.actionable_action == "buy" else "watch_trend",
                        rec.short_term_reversal or "none",
                    ]
                    for rec in buy_candidates[: args.market_limit]
                ]
                _print_text_table(buy_headers, buy_rows)
                print("Note: reason=watch_trend means this is a watchlist dip, not a direct buy call.")
            print()

            print("Risky dip watchlist (deep drops, avoid panic buying):")
            if not risky_dip_watchlist:
                print("No risky free-fall items right now.")
                print()
                return

            risk_headers = [
                "Type",
                "Currency",
                "1h",
                "12h",
                "24h",
                "Can Buy",
                "Signal",
            ]
            risk_rows = [
                [
                    rec.market_type,
                    rec.target_name,
                    f"{_format_dutch_number(rec.trend_1h_percent, 2)}%" if rec.trend_1h_percent is not None else "n/a",
                    f"{_format_dutch_number(rec.trend_12h_percent, 2)}%" if rec.trend_12h_percent is not None else "n/a",
                    f"{_format_dutch_number(rec.trend_24h_percent, 2)}%" if rec.trend_24h_percent is not None else "n/a",
                    str(rec.whole_units_affordable),
                    rec.short_term_reversal or "none",
                ]
                for rec in risky_dip_watchlist[: args.market_limit]
            ]
            _print_text_table(risk_headers, risk_rows)
            print()
            return

        print("POE Helper market fetch complete.")
        print(f"Snapshot written: {response.snapshot_path}")

        if response.trend_highlights:
            print("Top short-term reversals (bullish/bearish):")
            trend_headers = [
                "Reversal",
                "Target",
                "Target ID",
                "1h",
                "2h",
                "12h",
                "24h",
                "Chaos",
            ]
            trend_rows: list[list[str]] = []
            for row in response.trend_highlights:
                trend_rows.append(
                    [
                        row.short_term_reversal,
                        row.target_name,
                        row.target_currency,
                        f"{_format_dutch_number(row.trend_1h_percent, 2)}%" if row.trend_1h_percent is not None else "n/a",
                        f"{_format_dutch_number(row.trend_2h_percent, 2)}%" if row.trend_2h_percent is not None else "n/a",
                        f"{_format_dutch_number(row.trend_12h_percent, 2)}%" if row.trend_12h_percent is not None else "n/a",
                        f"{_format_dutch_number(row.trend_24h_percent, 2)}%" if row.trend_24h_percent is not None else "n/a",
                        _format_dutch_amount(row.latest_chaos_value) if row.latest_chaos_value is not None else "n/a",
                    ]
                )
            _print_text_table(trend_headers, trend_rows)

        if not response.top_entries:
            print("No market rows available in payload.")
            return

        print(f"Top {len(response.top_entries)} entries by chaos value:")
        for row in response.top_entries:
            print(f"- {row.name}: {_format_dutch_amount(row.chaos_value)} chaos")

        if args.vendor_file:
            if not response.ok and response.error and response.error_stage == "vendor":
                print(response.error)
                return
            if response.vendor_no_opportunities:
                log.info("No vendor opportunities found")
                print("No vendor comparison opportunities found for this snapshot.")
                return

            print(f"Vendor comparison opportunities (margin >= {_format_dutch_amount(args.min_margin)} chaos):")
            for row in response.vendor_opportunities[: args.market_limit]:
                print(
                    f"- {row.name}: market={_format_dutch_amount(row.market_chaos_value)}, "
                    f"vendor={_format_dutch_amount(row.vendor_chaos_cost)}, margin={_format_dutch_amount(row.margin_chaos)} chaos"
                )

        if args.convert:
            if not response.ok and response.error and response.error_stage == "convert":
                print(response.error)
                return
            if response.conversion is None:
                return

            print(
                f"Conversion: {_format_dutch_amount(response.conversion.amount)} {response.conversion.from_currency} ~= "
                f"{_format_dutch_amount(response.conversion.converted_amount)} {response.conversion.to_currency}"
            )

        if args.flip_route_file or args.flip_route_name:
            if not response.ok and response.error and response.error_stage == "flip":
                print(response.error)
                if response.available_routes:
                    print(f"Available routes: {', '.join(response.available_routes)}")
                return
            if response.flip_simulation is None:
                return

            print(f"Flip route: {response.flip_simulation.route_name}")
            for note in response.flip_simulation.step_notes:
                print(f"- {note}")
            print(
                f"Result: start={_format_dutch_amount(response.flip_simulation.start_amount)} {response.flip_simulation.start_currency}, "
                f"end={_format_dutch_amount(response.flip_simulation.end_amount)} {response.flip_simulation.end_currency}"
            )
            print(
                f"Chaos PnL: cost={_format_dutch_amount(response.flip_simulation.cost_chaos)}, "
                f"revenue={_format_dutch_amount(response.flip_simulation.revenue_chaos)}, "
                f"profit={_format_dutch_amount(response.flip_simulation.profit_chaos)}, "
                f"roi={_format_dutch_number(response.flip_simulation.roi_percent, 2)}%"
            )
        return

    init_result, manager = initialize_filter_manager(args.filter_dir)
    if not init_result.ok or manager is None:
        log.warning("Filter manager initialization failed", extra={"error": init_result.error})
        print(init_result.error)
        return

    log.info("Filter workflow started", extra={"directory": init_result.filter_directory})
    print("POE Helper started.")
    print(f"Filter directory: {init_result.filter_directory}")

    if args.list:
        list_result = list_filters(manager)
        if not list_result.ok and list_result.error:
            print(list_result.error)
            return
        if not list_result.filters:
            print(f"No filter files found in: {list_result.filter_directory}")
            return
        print("Available filters:")
        for name in list_result.filters:
            print(f"- {name}")
        return

    if args.build:
        build_result = build_filter(manager, args.source, args.output, args.profile)
        if not build_result.ok and build_result.error:
            print(build_result.error)
            if build_result.error.startswith("Filter not found:"):
                print("Tip: run with --list to see available source filenames for this directory.")
            return
        log.info("Managed filter written", extra={"output": build_result.output_path, "profile": args.profile})
        print(f"Managed filter written: {build_result.output_path}")
        return

    print("Tip: use --list or --build for filters, or --market for poe.ninja snapshots.")


if __name__ == "__main__":
    main()
