from __future__ import annotations

import argparse
import logging

from app.application.services import build_filter, execute_market_workflow, initialize_filter_manager, list_filters
from app.observability import configure_logging, tail_log_file


log = logging.getLogger("poe-helper")


def _format_dutch_number(value: float, decimals: int = 3) -> str:
    formatted = format(value, f",.{decimals}f")
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _format_dutch_amount(value: float, decimals: int = 3) -> str:
    return _format_dutch_number(value, decimals)


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
    parser.add_argument("--from-currency", type=str, default=None, help="Source currency id or name")
    parser.add_argument("--source-currency", type=str, default=None, help="Source currency for recommendation ranking")
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

    if args.tail_logs or args.follow_logs:
        log.info("Log tail requested")
        tail_log_file(str(log_file_path), lines=args.log_lines, follow=args.follow_logs)
        return

    if args.market:
        log.info("Market workflow started", extra={"league": args.league, "market_type": args.market_type})
        response = execute_market_workflow(
            league=args.league,
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
        )
        if not response.ok and response.error and response.error_stage == "fetch":
            print(response.error)
            return

        print("POE Helper market fetch complete.")
        print(f"Snapshot written: {response.snapshot_path}")

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

        if args.recommend:
            if not response.ok and response.error and response.error_stage == "recommend":
                print(response.error)
                return
            if not response.recommendations:
                print("No recommendation opportunities found for the selected source currency.")
                return

            print(f"Currency conversion overview from {args.source_currency or args.from_currency}:")
            for rec in response.recommendations:
                exalt_value = rec.value_exalt if rec.value_exalt is not None else 0.0
                print(
                    f"- {rec.target_name}: {_format_dutch_amount(rec.converted_amount)} {rec.target_currency} "
                    f"(~ {_format_dutch_number(rec.value_divine, 6)} divine / {_format_dutch_amount(rec.value_chaos)} chaos / {_format_dutch_amount(exalt_value)} exalt)"
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
