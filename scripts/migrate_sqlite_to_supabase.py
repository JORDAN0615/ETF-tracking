from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


TABLES = ["etfs", "holdings_snapshots", "holding_diffs", "crawl_runs"]


def _table_count_sqlite(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _table_count_pg(connection: psycopg.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count_value FROM {table}").fetchone()
    return int(row["count_value"])


def _fetch_sqlite_rows(connection: sqlite3.Connection, table: str) -> list[dict]:
    rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    return [dict(row) for row in rows]


def _migrate_etfs(pg: psycopg.Connection, rows: list[dict]) -> int:
    payload = [
        (
            row["ticker"],
            row["name"],
            row["source_type"],
            row["source_url"],
            row["source_config"],
            bool(row["is_active"]),
        )
        for row in rows
    ]
    if not payload:
        return 0
    with pg.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO etfs (ticker, name, source_type, source_url, source_config, is_active)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (ticker) DO UPDATE
            SET
                name = EXCLUDED.name,
                source_type = EXCLUDED.source_type,
                source_url = EXCLUDED.source_url,
                source_config = EXCLUDED.source_config,
                is_active = EXCLUDED.is_active
            """,
            payload,
        )
    return len(payload)


def _migrate_snapshots(pg: psycopg.Connection, rows: list[dict]) -> int:
    payload = [
        (
            row["etf_ticker"],
            row["trade_date"],
            row["fetched_at"],
            row["instrument_key"],
            row["instrument_name"],
            row["instrument_type"],
            row["quantity"],
            row["weight"],
        )
        for row in rows
    ]
    if not payload:
        return 0
    with pg.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO holdings_snapshots (
                etf_ticker, trade_date, fetched_at, instrument_key, instrument_name, instrument_type, quantity, weight
            )
            VALUES (%s, %s::date, %s::timestamptz, %s, %s, %s, %s, %s)
            ON CONFLICT (etf_ticker, trade_date, instrument_key) DO UPDATE
            SET
                fetched_at = EXCLUDED.fetched_at,
                instrument_name = EXCLUDED.instrument_name,
                instrument_type = EXCLUDED.instrument_type,
                quantity = EXCLUDED.quantity,
                weight = EXCLUDED.weight
            """,
            payload,
        )
    return len(payload)


def _migrate_diffs(pg: psycopg.Connection, rows: list[dict]) -> int:
    payload = [
        (
            row["etf_ticker"],
            row["trade_date"],
            row["instrument_key"],
            row["instrument_name"],
            row["change_type"],
            row["quantity_delta"],
            row["weight_delta"],
            row["prev_quantity"],
            row["curr_quantity"],
            row["prev_weight"],
            row["curr_weight"],
        )
        for row in rows
    ]
    if not payload:
        return 0
    with pg.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO holding_diffs (
                etf_ticker, trade_date, instrument_key, instrument_name, change_type,
                quantity_delta, weight_delta, prev_quantity, curr_quantity, prev_weight, curr_weight
            )
            VALUES (%s, %s::date, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (etf_ticker, trade_date, instrument_key) DO UPDATE
            SET
                instrument_name = EXCLUDED.instrument_name,
                change_type = EXCLUDED.change_type,
                quantity_delta = EXCLUDED.quantity_delta,
                weight_delta = EXCLUDED.weight_delta,
                prev_quantity = EXCLUDED.prev_quantity,
                curr_quantity = EXCLUDED.curr_quantity,
                prev_weight = EXCLUDED.prev_weight,
                curr_weight = EXCLUDED.curr_weight
            """,
            payload,
        )
    return len(payload)


def _migrate_crawl_runs(pg: psycopg.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0
    inserted = 0
    with pg.cursor() as cur:
        for row in rows:
            cur.execute(
            """
            INSERT INTO crawl_runs (etf_ticker, trigger_type, started_at, finished_at, status, trade_date, error_message)
            SELECT %s, %s, %s::timestamptz, %s::timestamptz, %s, %s::date, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM crawl_runs
                WHERE etf_ticker = %s
                  AND trigger_type = %s
                  AND started_at::timestamp = %s::timestamp
                  AND finished_at::timestamp = %s::timestamp
                  AND status = %s
                  AND trade_date IS NOT DISTINCT FROM %s::date
                  AND error_message IS NOT DISTINCT FROM %s
            )
            """,
            (
                row["etf_ticker"],
                row["trigger_type"],
                row["started_at"],
                row["finished_at"],
                row["status"],
                row["trade_date"],
                row["error_message"],
                row["etf_ticker"],
                row["trigger_type"],
                row["started_at"],
                row["finished_at"],
                row["status"],
                row["trade_date"],
                row["error_message"],
            ),
            )
            inserted += cur.rowcount
    return inserted


def _sample_verify(sqlite_conn: sqlite3.Connection, pg_conn: psycopg.Connection) -> None:
    samples = [("00980A", "2026-03-30"), ("00991A", "2026-03-30"), ("00992A", "2026-03-30")]
    print("\n[Sample verification]")
    for ticker, trade_date in samples:
        sqlite_count = sqlite_conn.execute(
            """
            SELECT COUNT(*) FROM holdings_snapshots WHERE etf_ticker = ? AND trade_date = ?
            """,
            (ticker, trade_date),
        ).fetchone()[0]
        pg_count = pg_conn.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM holdings_snapshots
            WHERE etf_ticker = %s AND trade_date = %s::date
            """,
            (ticker, trade_date),
        ).fetchone()["count_value"]
        print(f"{ticker} {trade_date}: sqlite={sqlite_count}, postgres={pg_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local SQLite data into Supabase/Postgres.")
    parser.add_argument(
        "--sqlite-path",
        default="data/etf_tracking.db",
        help="Path to source sqlite database (default: data/etf_tracking.db)",
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="Target Postgres DATABASE_URL (Supabase).",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(
        args.database_url,
        row_factory=dict_row,
        prepare_threshold=None,
    )

    try:
        print("[Before] table counts")
        for table in TABLES:
            print(f"- sqlite.{table}={_table_count_sqlite(sqlite_conn, table)}")
            print(f"- pg.{table}={_table_count_pg(pg_conn, table)}")

        etf_rows = _fetch_sqlite_rows(sqlite_conn, "etfs")
        snapshot_rows = _fetch_sqlite_rows(sqlite_conn, "holdings_snapshots")
        diff_rows = _fetch_sqlite_rows(sqlite_conn, "holding_diffs")
        crawl_rows = _fetch_sqlite_rows(sqlite_conn, "crawl_runs")

        print("\n[Migrate]")
        print(f"- etfs: { _migrate_etfs(pg_conn, etf_rows) } rows upserted")
        print(f"- holdings_snapshots: { _migrate_snapshots(pg_conn, snapshot_rows) } rows upserted")
        print(f"- holding_diffs: { _migrate_diffs(pg_conn, diff_rows) } rows upserted")
        print(f"- crawl_runs: { _migrate_crawl_runs(pg_conn, crawl_rows) } rows inserted")
        pg_conn.commit()

        print("\n[After] table counts")
        for table in TABLES:
            print(f"- sqlite.{table}={_table_count_sqlite(sqlite_conn, table)}")
            print(f"- pg.{table}={_table_count_pg(pg_conn, table)}")

        _sample_verify(sqlite_conn, pg_conn)
        print("\nMigration done.")
    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
