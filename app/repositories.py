from __future__ import annotations

import json
from datetime import date, datetime
from typing import Iterable, Optional

from app.db import get_connection, is_postgres
from app.models import ETF, Holding, HoldingDiff


DEFAULT_ETFS = [
    ETF(
        ticker="00980A",
        name="野村臺灣智慧優選主動式ETF",
        source_type="nomura_etfweb",
        source_url="https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00980A&tab=Shareholding",
        source_config={"fund_no": "00980A"},
    ),
    ETF(
        ticker="00981A",
        name="統一台股增長主動式ETF基金",
        source_type="unified_ezmoney",
        source_url="https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=49YTW",
        source_config={"fund_code": "49YTW"},
    ),
    ETF(
        ticker="00991A",
        name="復華台灣未來50主動式ETF基金",
        source_type="fhtrust_etf_html",
        source_url="https://www.fhtrust.com.tw/ETF/etf_detail/ETF23#stockhold",
        source_config={"etf_id": "ETF23"},
    ),
    ETF(
        ticker="00987A",
        name="台新臺灣優勢成長主動式ETF基金",
        source_type="tsit_etf_detail",
        source_url="https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/00987A",
        source_config={"fund_no": "00987A"},
    ),
    ETF(
        ticker="00992A",
        name="群益台灣科技創新主動式ETF",
        source_type="capital_portfolio",
        source_url="https://www.capitalfund.com.tw/etf/product/detail/500/portfolio",
        source_config={"fund_id": "500"},
    ),
]


def _normalize_value(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _row_to_dict(row) -> dict:
    return {key: _normalize_value(value) for key, value in dict(row).items()}


def _deserialize_etf(row) -> dict:
    etf = _row_to_dict(row)
    source_config = etf.get("source_config")
    if isinstance(source_config, str):
        etf["source_config"] = json.loads(source_config)
    else:
        etf["source_config"] = source_config or {}
    etf["is_active"] = bool(etf["is_active"])
    return etf


def seed_default_data() -> None:
    seed_rows_pg = [
        (
            etf.ticker,
            etf.name,
            etf.source_type,
            etf.source_url,
            json.dumps(etf.source_config, ensure_ascii=True),
            bool(etf.is_active),
        )
        for etf in DEFAULT_ETFS
    ]
    seed_rows_sqlite = [
        (
            etf.ticker,
            etf.name,
            etf.source_type,
            etf.source_url,
            json.dumps(etf.source_config, ensure_ascii=True),
            int(etf.is_active),
        )
        for etf in DEFAULT_ETFS
    ]
    with get_connection() as connection:
        if is_postgres():
            connection.executemany(
                """
                INSERT INTO etfs (
                    ticker, name, source_type, source_url, source_config, is_active
                )
                VALUES (?, ?, ?, ?, ?::jsonb, ?::boolean)
                ON CONFLICT (ticker) DO NOTHING
                """,
                seed_rows_pg,
            )
        else:
            connection.executemany(
                """
                INSERT OR IGNORE INTO etfs (
                    ticker, name, source_type, source_url, source_config, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                seed_rows_sqlite,
            )


def remove_etf(ticker: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM crawl_runs WHERE etf_ticker = ?", (ticker,))
        connection.execute("DELETE FROM holding_diffs WHERE etf_ticker = ?", (ticker,))
        connection.execute("DELETE FROM holdings_snapshots WHERE etf_ticker = ?", (ticker,))
        connection.execute("DELETE FROM etfs WHERE ticker = ?", (ticker,))


def list_etfs() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                e.ticker,
                e.name,
                e.source_type,
                e.source_url,
                e.source_config,
                e.is_active
            FROM etfs e
            ORDER BY e.ticker
            """
        ).fetchall()
    etfs = []
    for row in rows:
        etf = _deserialize_etf(row)
        metadata = get_latest_snapshot_metadata(etf["ticker"])
        latest_run = get_latest_crawl_run(etf["ticker"])
        etf["latest_trade_date"] = metadata["trade_date"] if metadata else None
        etf["latest_fetched_at"] = metadata["fetched_at"] if metadata else None
        etf["last_run_status"] = latest_run["status"] if latest_run else None
        etf["last_run_finished_at"] = latest_run["finished_at"] if latest_run else None
        etf["last_run_error"] = latest_run["error_message"] if latest_run else None
        etfs.append(etf)
    return etfs


def get_etf(ticker: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT ticker, name, source_type, source_url, source_config, is_active
            FROM etfs
            WHERE ticker = ?
            """,
            (ticker,),
        ).fetchone()
    return _deserialize_etf(row) if row else None


def save_snapshot(
    ticker: str,
    trade_date: str,
    holdings: Iterable[Holding],
    fetched_at: Optional[str] = None,
) -> None:
    snapshot_time = fetched_at or datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM holdings_snapshots WHERE etf_ticker = ? AND trade_date = ?",
            (ticker, trade_date),
        )
        connection.executemany(
            """
            INSERT INTO holdings_snapshots (
                etf_ticker, trade_date, fetched_at, instrument_key, instrument_name,
                instrument_type, quantity, weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    ticker,
                    trade_date,
                    snapshot_time,
                    holding.instrument_key,
                    holding.instrument_name,
                    holding.instrument_type,
                    holding.quantity,
                    holding.weight,
                )
                for holding in holdings
            ],
        )


def get_snapshot(ticker: str, trade_date: str) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT etf_ticker, trade_date, fetched_at, instrument_key, instrument_name,
                   instrument_type, quantity, weight
            FROM holdings_snapshots
            WHERE etf_ticker = ? AND trade_date = ?
            ORDER BY weight DESC, instrument_key
            """,
            (ticker, trade_date),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_previous_trade_date(ticker: str, trade_date: str) -> Optional[str]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT trade_date
            FROM holdings_snapshots
            WHERE etf_ticker = ? AND trade_date < ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (ticker, trade_date),
        ).fetchone()
    return row["trade_date"] if row else None


def save_diffs(ticker: str, trade_date: str, diffs: Iterable[HoldingDiff]) -> None:
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM holding_diffs WHERE etf_ticker = ? AND trade_date = ?",
            (ticker, trade_date),
        )
        connection.executemany(
            """
            INSERT INTO holding_diffs (
                etf_ticker, trade_date, instrument_key, instrument_name,
                change_type, quantity_delta, weight_delta, prev_quantity, curr_quantity,
                prev_weight, curr_weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    ticker,
                    trade_date,
                    diff.instrument_key,
                    diff.instrument_name,
                    diff.change_type,
                    diff.quantity_delta,
                    diff.weight_delta,
                    diff.prev_quantity,
                    diff.curr_quantity,
                    diff.prev_weight,
                    diff.curr_weight,
                )
                for diff in diffs
            ],
        )


def replace_snapshot_and_diffs(
    ticker: str,
    trade_date: str,
    holdings: Iterable[Holding],
    diffs: Iterable[HoldingDiff],
    fetched_at: str,
    trigger_type: str,
    started_at: str,
    finished_at: str,
) -> None:
    holdings_to_save = list(holdings)
    diffs_to_save = list(diffs)
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM holding_diffs WHERE etf_ticker = ? AND trade_date = ?",
            (ticker, trade_date),
        )
        connection.execute(
            "DELETE FROM holdings_snapshots WHERE etf_ticker = ? AND trade_date = ?",
            (ticker, trade_date),
        )
        connection.executemany(
            """
            INSERT INTO holdings_snapshots (
                etf_ticker, trade_date, fetched_at, instrument_key, instrument_name,
                instrument_type, quantity, weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    ticker,
                    trade_date,
                    fetched_at,
                    holding.instrument_key,
                    holding.instrument_name,
                    holding.instrument_type,
                    holding.quantity,
                    holding.weight,
                )
                for holding in holdings_to_save
            ],
        )
        if diffs_to_save:
            connection.executemany(
                """
                INSERT INTO holding_diffs (
                    etf_ticker, trade_date, instrument_key, instrument_name,
                    change_type, quantity_delta, weight_delta, prev_quantity, curr_quantity,
                    prev_weight, curr_weight
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        ticker,
                        trade_date,
                        diff.instrument_key,
                        diff.instrument_name,
                        diff.change_type,
                        diff.quantity_delta,
                        diff.weight_delta,
                        diff.prev_quantity,
                        diff.curr_quantity,
                        diff.prev_weight,
                        diff.curr_weight,
                    )
                    for diff in diffs_to_save
                ],
            )
        connection.execute(
            """
            INSERT INTO crawl_runs (
                etf_ticker, trigger_type, started_at, finished_at, status, trade_date, error_message
            )
            VALUES (?, ?, ?, ?, 'success', ?, NULL)
            """,
            (ticker, trigger_type, started_at, finished_at, trade_date),
        )


def record_crawl_run(
    ticker: str,
    trigger_type: str,
    started_at: str,
    finished_at: str,
    status: str,
    trade_date: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO crawl_runs (
                etf_ticker, trigger_type, started_at, finished_at, status, trade_date, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                trigger_type,
                started_at,
                finished_at,
                status,
                trade_date,
                error_message,
            ),
        )


def _serialize_diff_row(row) -> dict:
    payload = _row_to_dict(row)
    prev_quantity = payload["prev_quantity"]
    curr_quantity = payload["curr_quantity"]
    change_type = payload["change_type"]
    if change_type == "enter_top10":
        quantity_delta_pct = 100.0
    elif change_type == "exit_top10":
        quantity_delta_pct = -100.0
    elif prev_quantity in (None, 0):
        quantity_delta_pct = None
    else:
        quantity_delta_pct = payload["quantity_delta"] / prev_quantity * 100
    payload["quantity_delta_pct"] = quantity_delta_pct
    payload["quantity_delta_lots"] = payload["quantity_delta"] / 1000
    payload["prev_quantity_lots"] = prev_quantity / 1000 if prev_quantity is not None else None
    payload["curr_quantity_lots"] = curr_quantity / 1000 if curr_quantity is not None else None
    return payload


def get_diffs(ticker: str, trade_date: str) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT etf_ticker, trade_date, instrument_key, instrument_name,
                   change_type, quantity_delta, weight_delta, prev_quantity, curr_quantity,
                   prev_weight, curr_weight
            FROM holding_diffs
            WHERE etf_ticker = ? AND trade_date = ?
            ORDER BY
                CASE change_type
                    WHEN 'enter_top10' THEN 1
                    WHEN 'increase' THEN 2
                    WHEN 'decrease' THEN 3
                    WHEN 'exit_top10' THEN 4
                    ELSE 5
                END,
                ABS(COALESCE(weight_delta, 0)) DESC,
                instrument_key
            """,
            (ticker, trade_date),
        ).fetchall()
    return [_serialize_diff_row(row) for row in rows]


def get_latest_snapshot_date(ticker: str) -> Optional[str]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT trade_date
            FROM holdings_snapshots
            WHERE etf_ticker = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()
    return _normalize_value(row["trade_date"]) if row else None


def get_latest_snapshot_metadata(ticker: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT trade_date, fetched_at
            FROM holdings_snapshots
            WHERE etf_ticker = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_snapshot_metadata(ticker: str, trade_date: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT trade_date, fetched_at
            FROM holdings_snapshots
            WHERE etf_ticker = ? AND trade_date = ?
            LIMIT 1
            """,
            (ticker, trade_date),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_latest_snapshot_count(ticker: str) -> Optional[int]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS snapshot_count
            FROM holdings_snapshots
            WHERE etf_ticker = ?
              AND trade_date = (
                  SELECT MAX(trade_date)
                  FROM holdings_snapshots
                  WHERE etf_ticker = ?
              )
            """,
            (ticker, ticker),
        ).fetchone()
    if not row or row["snapshot_count"] == 0:
        return None
    return int(row["snapshot_count"])


def get_latest_crawl_run(ticker: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, etf_ticker, trigger_type, started_at, finished_at, status, trade_date, error_message
            FROM crawl_runs
            WHERE etf_ticker = ?
            ORDER BY finished_at DESC, id DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()
    return _row_to_dict(row) if row else None
