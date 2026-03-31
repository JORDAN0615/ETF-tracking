from __future__ import annotations

import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    override = os.getenv("ETF_TRACKING_DB_PATH")
    if override:
        return Path(override)
    # Vercel serverless file system is read-only except /tmp.
    if os.getenv("VERCEL") == "1":
        return Path("/tmp/etf_tracking.db")
    return BASE_DIR / "data" / "etf_tracking.db"


def get_data_dir() -> Path:
    return get_db_path().parent


def get_connection() -> sqlite3.Connection:
    get_data_dir().mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(get_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS etfs (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_config TEXT NOT NULL DEFAULT '{}',
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS holdings_snapshots (
                etf_ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                fetched_at TEXT,
                instrument_key TEXT NOT NULL,
                instrument_name TEXT NOT NULL,
                instrument_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                weight REAL,
                PRIMARY KEY (etf_ticker, trade_date, instrument_key),
                FOREIGN KEY (etf_ticker) REFERENCES etfs (ticker)
            );

            CREATE TABLE IF NOT EXISTS holding_diffs (
                etf_ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                instrument_key TEXT NOT NULL,
                instrument_name TEXT NOT NULL,
                change_type TEXT NOT NULL,
                quantity_delta REAL NOT NULL,
                weight_delta REAL,
                prev_quantity REAL,
                curr_quantity REAL,
                prev_weight REAL,
                curr_weight REAL,
                PRIMARY KEY (etf_ticker, trade_date, instrument_key),
                FOREIGN KEY (etf_ticker) REFERENCES etfs (ticker)
            );

            CREATE TABLE IF NOT EXISTS crawl_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                etf_ticker TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                trade_date TEXT,
                error_message TEXT,
                FOREIGN KEY (etf_ticker) REFERENCES etfs (ticker)
            );
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(holdings_snapshots)").fetchall()
        }
        if "fetched_at" not in columns:
            connection.execute(
                "ALTER TABLE holdings_snapshots ADD COLUMN fetched_at TEXT"
            )
