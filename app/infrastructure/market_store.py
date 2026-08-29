from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


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
            "CREATE INDEX IF NOT EXISTS idx_market_rows_latest ON market_rows(league, market_type, item_id, fetched_at)"
        )
        self._conn.commit()

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
