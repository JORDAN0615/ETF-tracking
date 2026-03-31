from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.adapters import get_adapter
from app.models import Holding
from app.repositories import (
    get_etf,
    get_latest_snapshot_count,
    get_previous_trade_date,
    get_snapshot,
    record_crawl_run,
    replace_snapshot_and_diffs,
    list_etfs,
)
from app.services.diff import build_diffs


def _rows_to_holdings(rows: list[dict]) -> list[Holding]:
    return [
        Holding(
            instrument_key=row["instrument_key"],
            instrument_name=row["instrument_name"],
            instrument_type=row["instrument_type"],
            quantity=row["quantity"],
            weight=row["weight"],
        )
        for row in rows
    ]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _validate_snapshot(
    ticker: str,
    trade_date: str,
    holdings: list[Holding],
) -> None:
    if not trade_date:
        raise ValueError("Missing trade_date from source data")
    if not holdings:
        raise ValueError("No holdings parsed from source data")

    seen_keys = set()
    for holding in holdings:
        if not holding.instrument_key:
            raise ValueError("Holding missing instrument_key")
        if not holding.instrument_name:
            raise ValueError(f"Holding {holding.instrument_key} missing instrument_name")
        if holding.quantity is None or holding.quantity < 0:
            raise ValueError(f"Holding {holding.instrument_key} has invalid quantity")
        if holding.weight is not None and holding.weight < 0:
            raise ValueError(f"Holding {holding.instrument_key} has invalid weight")
        if holding.instrument_key in seen_keys:
            raise ValueError(f"Duplicate holding instrument_key: {holding.instrument_key}")
        seen_keys.add(holding.instrument_key)

    baseline_count = get_latest_snapshot_count(ticker)
    if baseline_count and len(holdings) < baseline_count * 0.5:
        raise ValueError(
            f"Parsed holdings count {len(holdings)} is too low versus previous baseline {baseline_count}"
        )


def ingest_latest_snapshot(
    ticker: str,
    trigger_type: str = "manual",
    target_date: Optional[str] = None,
) -> dict:
    etf = get_etf(ticker)
    if not etf:
        raise ValueError(f"Unknown ETF ticker: {ticker}")

    started_at = _now_iso()
    trade_date: Optional[str] = None
    try:
        source_config = dict(etf["source_config"])
        if target_date:
            source_config["target_date"] = target_date
        adapter = get_adapter(etf["source_type"])
        raw_data = adapter.fetch(etf["source_url"], source_config)
        trade_date, holdings = adapter.parse(raw_data, source_config)
        _validate_snapshot(ticker, trade_date, holdings)

        previous_trade_date = get_previous_trade_date(ticker, trade_date)
        previous_rows = get_snapshot(ticker, previous_trade_date) if previous_trade_date else []
        diffs = build_diffs(_rows_to_holdings(previous_rows), holdings) if previous_trade_date else []
        fetched_at = _now_iso()
        replace_snapshot_and_diffs(
            ticker=ticker,
            trade_date=trade_date,
            holdings=holdings,
            diffs=diffs,
            fetched_at=fetched_at,
            trigger_type=trigger_type,
            started_at=started_at,
            finished_at=fetched_at,
        )
    except Exception as exc:
        failed_at = _now_iso()
        record_crawl_run(
            ticker=ticker,
            trigger_type=trigger_type,
            started_at=started_at,
            finished_at=failed_at,
            status="failed",
            trade_date=trade_date,
            error_message=str(exc),
        )
        return {
            "ticker": ticker,
            "status": "failed",
            "trade_date": trade_date,
            "target_date": target_date,
            "failed_at": failed_at,
            "error_message": str(exc),
        }

    return {
        "ticker": ticker,
        "status": "success",
        "trade_date": trade_date,
        "target_date": target_date,
        "fetched_at": fetched_at,
        "snapshot_count": len(holdings),
        "diff_count": len(diffs),
        "previous_trade_date": previous_trade_date,
    }


def refresh_active_etfs(trigger_type: str = "manual") -> dict:
    results = []
    for etf in list_etfs():
        if not etf["is_active"]:
            continue
        results.append(ingest_latest_snapshot(etf["ticker"], trigger_type=trigger_type))
    return {
        "trigger_type": trigger_type,
        "refreshed_at": _now_iso(),
        "results": results,
    }
