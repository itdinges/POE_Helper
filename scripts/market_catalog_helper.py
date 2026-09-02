from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.market_types import get_market_types_for_category, load_market_type_config


CONFIG_PATH = Path("config/market_types.json")
DB_PATH = Path("data/market/poe_market.db")


def _print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def _load_configured_types() -> dict[str, list[str]]:
    config = load_market_type_config(CONFIG_PATH)
    return {
        "default": get_market_types_for_category(config, "default"),
        "optional": get_market_types_for_category(config, "optional"),
        "progression": get_market_types_for_category(config, "progression"),
        "equipment": get_market_types_for_category(config, "equipment"),
    }


def _db_counts() -> dict[str, int]:
    if not DB_PATH.exists():
        return {}

    connection = sqlite3.connect(str(DB_PATH))
    try:
        rows = connection.execute(
            "SELECT market_type, COUNT(*) FROM market_rows GROUP BY market_type ORDER BY market_type"
        ).fetchall()
    finally:
        connection.close()

    return {market_type: int(count) for market_type, count in rows}


def main() -> None:
    configured = _load_configured_types()
    counts = _db_counts()

    _print_section("Configured market fetch types")
    for category in ("default", "optional", "progression", "equipment"):
        names = configured[category]
        if not names:
            print(f"{category}: none")
            continue
        print(f"{category}: {', '.join(names)}")

    _print_section("Database population summary")
    if not counts:
        print("No market rows found in the SQLite database yet.")
        return

    for category in ("default", "optional", "progression", "equipment"):
        names = configured[category]
        if not names:
            continue
        print(f"{category}:")
        for name in names:
            count = counts.get(name, 0)
            print(f"  - {name}: {count} rows")


if __name__ == "__main__":
    main()
