from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent


class PostgresCompatConnection:
    """Minimal compatibility wrapper for existing sqlite-style repository SQL."""

    def __init__(self, connection: psycopg.Connection):
        self._connection = connection

    def _adapt_query(self, query: str) -> str:
        return query.replace("?", "%s")

    def execute(self, query: str, params=None):
        adapted = self._adapt_query(query)
        if params is None:
            return self._connection.execute(adapted)
        return self._connection.execute(adapted, params)

    def executemany(self, query: str, params_seq):
        with self._connection.cursor() as cursor:
            cursor.executemany(self._adapt_query(query), params_seq)
            return cursor

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._connection.__exit__(exc_type, exc_val, exc_tb)


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


def is_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def get_connection():
    if is_postgres():
        connection = psycopg.connect(
            os.environ["DATABASE_URL"],
            row_factory=dict_row,
            prepare_threshold=None,
        )
        connection.autocommit = False
        return PostgresCompatConnection(connection)
    get_data_dir().mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(get_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    if is_postgres():
        _init_postgres()
        return
    _init_sqlite()


def _init_sqlite() -> None:
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

            CREATE TABLE IF NOT EXISTS my_holdings (
                trade_date  TEXT NOT NULL,
                ticker      TEXT NOT NULL,
                name        TEXT NOT NULL,
                close_price REAL NOT NULL,
                shares      INTEGER NOT NULL,
                market_value REAL NOT NULL,
                source_file TEXT,
                imported_at TEXT NOT NULL,
                PRIMARY KEY (trade_date, ticker)
            );

            CREATE TABLE IF NOT EXISTS us_stock_transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date  TEXT NOT NULL,
                ticker      TEXT NOT NULL,
                name        TEXT,
                action      TEXT NOT NULL,
                shares      REAL NOT NULL,
                price       REAL,
                source_file TEXT,
                imported_at TEXT NOT NULL
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


def _init_postgres() -> None:
    statements: Iterator[str] = iter(
        [
            """
            CREATE TABLE IF NOT EXISTS etfs (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_config JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS holdings_snapshots (
                etf_ticker TEXT NOT NULL REFERENCES etfs (ticker),
                trade_date DATE NOT NULL,
                fetched_at TIMESTAMPTZ,
                instrument_key TEXT NOT NULL,
                instrument_name TEXT NOT NULL,
                instrument_type TEXT NOT NULL,
                quantity DOUBLE PRECISION NOT NULL,
                weight DOUBLE PRECISION,
                PRIMARY KEY (etf_ticker, trade_date, instrument_key)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS holding_diffs (
                etf_ticker TEXT NOT NULL REFERENCES etfs (ticker),
                trade_date DATE NOT NULL,
                instrument_key TEXT NOT NULL,
                instrument_name TEXT NOT NULL,
                change_type TEXT NOT NULL,
                quantity_delta DOUBLE PRECISION NOT NULL,
                weight_delta DOUBLE PRECISION,
                prev_quantity DOUBLE PRECISION,
                curr_quantity DOUBLE PRECISION,
                prev_weight DOUBLE PRECISION,
                curr_weight DOUBLE PRECISION,
                PRIMARY KEY (etf_ticker, trade_date, instrument_key)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS crawl_runs (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                etf_ticker TEXT NOT NULL REFERENCES etfs (ticker),
                trigger_type TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL,
                trade_date DATE,
                error_message TEXT
            )
            """,
        ]
    )
    with get_connection() as connection:
        for stmt in statements:
            connection.execute(stmt)
