from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from app.domain.market_types import MarketTypeConfig


@dataclass(slots=True)
class MarketRowRecord:
    league: str
    market_type: str
    item_id: str
    item_name: str
    chaos_value: float
    primary_value: float
    fetched_at: datetime
    vendor_value: float | None = None


@dataclass(slots=True)
class MarketTypeCatalogRecord:
    category: str
    name: str
    enabled: bool = True


@dataclass(slots=True)
class MarketItemStatsRecord:
    league: str
    market_type: str
    item_id: str
    item_name: str
    latest_chaos_value: float
    trend_1h_percent: float | None = None
    trend_2h_percent: float | None = None
    trend_12h_percent: float | None = None
    trend_24h_percent: float | None = None
    short_term_reversal: str = "none"
    computed_at: datetime | None = None


class SQLiteMarketStore:
    def __init__(self, db_path: str | Path = "data/market/poe_market.db") -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def __enter__(self) -> "SQLiteMarketStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _initialize_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league TEXT NOT NULL,
                market_type TEXT NOT NULL,
                source_file TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league TEXT NOT NULL,
                market_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                chaos_value REAL NOT NULL,
                primary_value REAL NOT NULL,
                vendor_value REAL,
                fetched_at TEXT NOT NULL,
                snapshot_id INTEGER NOT NULL,
                UNIQUE(league, market_type, item_id, fetched_at),
                FOREIGN KEY(snapshot_id) REFERENCES market_snapshots(id)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_type_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                UNIQUE(category, name)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_rows_latest ON market_rows(league, market_type, item_id, fetched_at)"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_item_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league TEXT NOT NULL,
                market_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                latest_chaos_value REAL NOT NULL,
                trend_1h_percent REAL,
                trend_2h_percent REAL,
                trend_12h_percent REAL,
                trend_24h_percent REAL,
                short_term_reversal TEXT NOT NULL DEFAULT 'none',
                computed_at TEXT NOT NULL,
                UNIQUE(league, market_type, item_id)
            )
            """
        )
        self._ensure_market_item_stats_schema()
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_item_stats_latest ON market_item_stats(league, market_type, short_term_reversal)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_type_catalog_category ON market_type_catalog(category, enabled)"
        )
        self._conn.commit()

    def _ensure_market_item_stats_schema(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        existing_columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(market_item_stats)").fetchall()
        }

        required_columns = {
            "trend_1h_percent": "REAL",
            "trend_2h_percent": "REAL",
            "trend_12h_percent": "REAL",
            "trend_24h_percent": "REAL",
            "short_term_reversal": "TEXT NOT NULL DEFAULT 'none'",
            "computed_at": "TEXT NOT NULL DEFAULT ''",
        }

        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            self._conn.execute(
                f"ALTER TABLE market_item_stats ADD COLUMN {column_name} {column_type}"
            )

    def sync_market_types(self, config: MarketTypeConfig, *, source: str = "config") -> list[MarketTypeCatalogRecord]:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        entries: list[MarketTypeCatalogRecord] = []
        for entry in config.entries():
            self._conn.execute(
                """
                INSERT OR REPLACE INTO market_type_catalog (category, name, enabled)
                VALUES (?, ?, ?)
                """,
                (entry.category, entry.name, int(entry.enabled)),
            )
            entries.append(MarketTypeCatalogRecord(category=entry.category, name=entry.name, enabled=entry.enabled))
        self._conn.commit()
        return entries

    def get_market_types(self, *, category: str | None = None) -> list[str]:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        if category is None:
            rows = self._conn.execute(
                "SELECT name FROM market_type_catalog WHERE enabled = 1 ORDER BY category, name"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT name FROM market_type_catalog WHERE category = ? AND enabled = 1 ORDER BY name",
                (category,),
            ).fetchall()

        return [row["name"] for row in rows]

    def save_snapshot_record(self, *, league: str, market_type: str, source_file: str, fetched_at: datetime) -> int:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        cursor = self._conn.execute(
            """
            INSERT INTO market_snapshots (league, market_type, source_file, fetched_at)
            VALUES (?, ?, ?, ?)
            """,
            (league, market_type, source_file, fetched_at.isoformat(timespec="seconds")),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def save_market_rows(self, rows: Iterable[MarketRowRecord]) -> None:
        batch = list(rows)
        if not batch:
            return

        snapshot_id = self.save_snapshot_record(
            league=batch[0].league,
            market_type=batch[0].market_type,
            source_file="live-fetch",
            fetched_at=batch[0].fetched_at,
        )

        self._conn.executemany(
            """
            INSERT OR REPLACE INTO market_rows (
                league, market_type, item_id, item_name, chaos_value, primary_value, vendor_value, fetched_at, snapshot_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.league,
                    row.market_type,
                    row.item_id,
                    row.item_name,
                    row.chaos_value,
                    row.primary_value,
                    row.vendor_value,
                    row.fetched_at.isoformat(timespec="seconds"),
                    snapshot_id,
                )
                for row in batch
            ],
        )
        self._conn.commit()

    def reset_database(self) -> None:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        self._conn.executescript(
            """
            DELETE FROM market_rows;
            DELETE FROM market_snapshots;
            DELETE FROM market_item_stats;
            DELETE FROM market_type_catalog;
            DELETE FROM sqlite_sequence
            WHERE name IN ('market_rows', 'market_snapshots', 'market_item_stats', 'market_type_catalog');
            """
        )
        self._conn.commit()

    def refresh_market_item_stats(self, league: str, market_type: str) -> int:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        rows = self._conn.execute(
            """
            SELECT item_id, item_name, chaos_value, fetched_at
            FROM market_rows
            WHERE league = ? AND market_type = ?
            ORDER BY item_id, fetched_at ASC
            """,
            (league, market_type),
        ).fetchall()

        if not rows:
            self._conn.execute(
                "DELETE FROM market_item_stats WHERE league = ? AND market_type = ?",
                (league, market_type),
            )
            self._conn.commit()
            return 0

        by_item: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            by_item.setdefault(row["item_id"], []).append(row)

        computed_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        existing_columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(market_item_stats)").fetchall()
        }

        insert_rows: list[dict[str, object]] = []
        for item_id, history in by_item.items():
            latest = history[-1]
            latest_value = float(latest["chaos_value"])
            latest_time = datetime.fromisoformat(latest["fetched_at"])
            previous_value = float(history[-2]["chaos_value"]) if len(history) > 1 else None
            delta_chaos = (latest_value - previous_value) if previous_value is not None else None
            delta_percent = ((delta_chaos / previous_value) * 100.0) if previous_value and previous_value > 0 and delta_chaos is not None else None
            trend = "flat"
            if delta_chaos is not None:
                if delta_chaos > 0:
                    trend = "up"
                elif delta_chaos < 0:
                    trend = "down"

            trailing_values = [float(row["chaos_value"]) for row in history]
            avg_chaos_3 = self._mean(trailing_values[-3:])
            avg_chaos_7 = self._mean(trailing_values[-7:])
            volatility_7 = self._relative_volatility(trailing_values[-7:])

            trend_1h = self._compute_percent_change(history, latest_time, hours=1)
            trend_2h = self._compute_percent_change(history, latest_time, hours=2)
            trend_12h = self._compute_percent_change(history, latest_time, hours=12)
            trend_24h = self._compute_percent_change(history, latest_time, hours=24)
            reversal = self._classify_short_term_reversal(
                trend_1h=trend_1h,
                trend_2h=trend_2h,
                trend_24h=trend_24h,
            )

            insert_rows.append(
                {
                    "league": league,
                    "market_type": market_type,
                    "item_id": item_id,
                    "item_name": str(latest["item_name"]),
                    "observations": len(history),
                    "latest_fetched_at": latest["fetched_at"],
                    "latest_chaos_value": latest_value,
                    "previous_chaos_value": previous_value,
                    "delta_chaos": delta_chaos,
                    "delta_percent": delta_percent,
                    "trend": trend,
                    "avg_chaos_3": avg_chaos_3,
                    "avg_chaos_7": avg_chaos_7,
                    "volatility_percent_7": volatility_7,
                    "trend_1h_percent": trend_1h,
                    "trend_2h_percent": trend_2h,
                    "trend_12h_percent": trend_12h,
                    "trend_24h_percent": trend_24h,
                    "trend_1d_percent": trend_24h,
                    "short_term_reversal": reversal,
                    "computed_at": computed_at,
                }
            )

        self._conn.execute(
            "DELETE FROM market_item_stats WHERE league = ? AND market_type = ?",
            (league, market_type),
        )
        insert_columns = [
            "league",
            "market_type",
            "item_id",
            "item_name",
            "observations",
            "latest_fetched_at",
            "latest_chaos_value",
            "previous_chaos_value",
            "delta_chaos",
            "delta_percent",
            "trend",
            "avg_chaos_3",
            "avg_chaos_7",
            "volatility_percent_7",
            "trend_1h_percent",
            "trend_2h_percent",
            "trend_12h_percent",
            "trend_24h_percent",
            "trend_1d_percent",
            "short_term_reversal",
            "computed_at",
        ]
        insert_columns = [column for column in insert_columns if column in existing_columns]
        placeholders = ", ".join("?" for _ in insert_columns)
        column_sql = ", ".join(insert_columns)
        values_rows = [tuple(row[column] for column in insert_columns) for row in insert_rows]

        self._conn.executemany(
            f"INSERT INTO market_item_stats ({column_sql}) VALUES ({placeholders})",  # nosec B608: columns come from fixed internal allowlist
            values_rows,
        )
        self._conn.commit()
        return len(insert_rows)

    def get_market_item_stats(self, league: str, market_type: str) -> list[MarketItemStatsRecord]:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        rows = self._conn.execute(
            """
            SELECT *
            FROM market_item_stats
            WHERE league = ? AND market_type = ?
            ORDER BY item_name
            """,
            (league, market_type),
        ).fetchall()

        parsed: list[MarketItemStatsRecord] = []
        for row in rows:
            computed_raw = row["computed_at"]
            computed_at = datetime.fromisoformat(computed_raw) if isinstance(computed_raw, str) else None
            parsed.append(
                MarketItemStatsRecord(
                    league=row["league"],
                    market_type=row["market_type"],
                    item_id=row["item_id"],
                    item_name=row["item_name"],
                    latest_chaos_value=float(row["latest_chaos_value"]),
                    trend_1h_percent=row["trend_1h_percent"],
                    trend_2h_percent=row["trend_2h_percent"],
                    trend_12h_percent=row["trend_12h_percent"],
                    trend_24h_percent=row["trend_24h_percent"],
                    short_term_reversal=str(row["short_term_reversal"] or "none"),
                    computed_at=computed_at,
                )
            )
        return parsed

    @staticmethod
    def _compute_percent_change(history: list[sqlite3.Row], latest_time: datetime, *, hours: int) -> float | None:
        cutoff = latest_time - timedelta(hours=hours)
        baseline_value: float | None = None
        for row in reversed(history[:-1]):
            row_time = datetime.fromisoformat(row["fetched_at"])
            if row_time <= cutoff:
                baseline_value = float(row["chaos_value"])
                break
        if baseline_value is None or baseline_value <= 0:
            return None

        latest_value = float(history[-1]["chaos_value"])
        return ((latest_value - baseline_value) / baseline_value) * 100.0

    @staticmethod
    def _classify_short_term_reversal(
        *,
        trend_1h: float | None,
        trend_2h: float | None,
        trend_24h: float | None,
    ) -> str:
        if trend_1h is None or trend_2h is None or trend_24h is None:
            return "none"

        # Bullish reversal: broader 24h downtrend but short-term momentum (1h/2h) turns up.
        if trend_24h < 0 and trend_1h > 0 and trend_2h > 0:
            return "bullish_reversal"

        # Bearish reversal: broader 24h uptrend but short-term momentum (1h/2h) turns down.
        if trend_24h > 0 and trend_1h < 0 and trend_2h < 0:
            return "bearish_reversal"

        return "none"

    @staticmethod
    def _mean(values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _relative_volatility(values: list[float]) -> float | None:
        if len(values) < 2:
            return None
        mean_value = SQLiteMarketStore._mean(values)
        if mean_value <= 0:
            return None
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        std_dev = variance ** 0.5
        return (std_dev / mean_value) * 100.0

    def get_latest_market_rows(self, league: str, market_type: str) -> list[MarketRowRecord]:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        rows = self._conn.execute(
            """
            WITH latest AS (
                SELECT item_id, MAX(fetched_at) AS fetched_at
                FROM market_rows
                WHERE league = ? AND market_type = ?
                GROUP BY item_id
            )
            SELECT mr.*
            FROM market_rows mr
            JOIN latest l
              ON mr.item_id = l.item_id
             AND mr.fetched_at = l.fetched_at
            WHERE mr.league = ? AND mr.market_type = ?
            ORDER BY mr.item_name
            """,
            (league, market_type, league, market_type),
        ).fetchall()

        return [
            MarketRowRecord(
                league=row["league"],
                market_type=row["market_type"],
                item_id=row["item_id"],
                item_name=row["item_name"],
                chaos_value=float(row["chaos_value"]),
                primary_value=float(row["primary_value"]),
                fetched_at=datetime.fromisoformat(row["fetched_at"]),
                vendor_value=row["vendor_value"],
            )
            for row in rows
        ]

    def get_item_history(self, league: str, market_type: str, item_id: str) -> list[MarketRowRecord]:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")

        rows = self._conn.execute(
            """
            SELECT *
            FROM market_rows
            WHERE league = ? AND market_type = ? AND item_id = ?
            ORDER BY fetched_at ASC
            """,
            (league, market_type, item_id),
        ).fetchall()

        return [
            MarketRowRecord(
                league=row["league"],
                market_type=row["market_type"],
                item_id=row["item_id"],
                item_name=row["item_name"],
                chaos_value=float(row["chaos_value"]),
                primary_value=float(row["primary_value"]),
                fetched_at=datetime.fromisoformat(row["fetched_at"]),
                vendor_value=row["vendor_value"],
            )
            for row in rows
        ]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
