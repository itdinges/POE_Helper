from __future__ import annotations

import argparse

from app.filter_manager import FilterManager


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        manager = FilterManager(
            filter_directory=args.filter_dir,
            create_if_missing=args.filter_dir is None,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(str(exc))
        return

    print("POE Helper started.")
    print(f"Filter directory: {manager.filter_directory}")

    if args.list:
        filters = manager.list_filters()
        if not filters:
            print(f"No filter files found in: {manager.filter_directory}")
            return
        print("Available filters:")
        for name in filters:
            print(f"- {name}")
        return

    if args.build:
        if not args.source or not args.output:
            print("--build requires both --source and --output.")
            return
        try:
            output = manager.create_managed_filter(args.source, args.output, args.profile)
        except FileNotFoundError as exc:
            print(str(exc))
            print("Tip: run with --list to see available source filenames for this directory.")
            return
        print(f"Managed filter written: {output}")
        return

    print("Tip: use --list to discover filters or --build to generate a managed filter.")


if __name__ == "__main__":
    main()
