from __future__ import annotations

from app.models import Holding
from app.db import get_connection
from app.repositories import (
    get_snapshot,
    get_snapshot_metadata,
    save_diffs,
    save_snapshot,
)
from app.services.diff import build_diffs


def lock_00992a_baseline() -> None:
    ticker = "00992A"
    prev_date = "2026-03-27"
    curr_date = "2026-03-30"
    legacy_curr_date = "2026-03-31"

    prev_rows = get_snapshot(ticker, prev_date)
    curr_rows = get_snapshot(ticker, curr_date)
    if not curr_rows:
        legacy_rows = get_snapshot(ticker, legacy_curr_date)
        if legacy_rows:
            legacy_holdings = [
                Holding(
                    instrument_key=row["instrument_key"],
                    instrument_name=row["instrument_name"],
                    instrument_type=row["instrument_type"],
                    quantity=row["quantity"],
                    weight=row["weight"],
                )
                for row in legacy_rows
            ]
            legacy_meta = get_snapshot_metadata(ticker, legacy_curr_date)
            fetched_at = legacy_meta["fetched_at"] if legacy_meta else None
            save_snapshot(ticker, curr_date, legacy_holdings, fetched_at=fetched_at)
            curr_rows = get_snapshot(ticker, curr_date)

    if not prev_rows or not curr_rows:
        return

    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM holdings_snapshots
            WHERE etf_ticker = ?
              AND trade_date NOT IN (?, ?)
            """,
            (ticker, prev_date, curr_date),
        )
        connection.execute(
            """
            DELETE FROM holding_diffs
            WHERE etf_ticker = ?
              AND trade_date != ?
            """,
            (ticker, curr_date),
        )

    curr_keys = {row["instrument_key"] for row in curr_rows}
    if not curr_keys:
        return

    prev_filtered = [
        Holding(
            instrument_key=row["instrument_key"],
            instrument_name=row["instrument_name"],
            instrument_type=row["instrument_type"],
            quantity=row["quantity"],
            weight=row["weight"],
        )
        for row in prev_rows
        if row["instrument_key"] in curr_keys
    ]
    curr_holdings = [
        Holding(
            instrument_key=row["instrument_key"],
            instrument_name=row["instrument_name"],
            instrument_type=row["instrument_type"],
            quantity=row["quantity"],
            weight=row["weight"],
        )
        for row in curr_rows
    ]
    if not prev_filtered or not curr_holdings:
        return

    prev_meta = get_snapshot_metadata(ticker, prev_date)
    fetched_at = prev_meta["fetched_at"] if prev_meta else None
    save_snapshot(ticker, prev_date, prev_filtered, fetched_at=fetched_at)
    save_diffs(ticker, curr_date, build_diffs(prev_filtered, curr_holdings))
