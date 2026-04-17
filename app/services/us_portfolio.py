from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from app.db import get_connection

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _get_us_positions() -> list[dict]:
    """從 us_stock_transactions 計算目前各 ticker 的持股數。"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                ticker,
                MAX(name) AS name,
                SUM(CASE WHEN action = 'sell' THEN -shares ELSE shares END) AS total_shares
            FROM us_stock_transactions
            GROUP BY ticker
            HAVING total_shares > 0.0001
            ORDER BY ticker
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _fetch_prices_and_rate(tickers: list[str]) -> tuple[dict[str, float], float | None]:
    """
    用 yfinance 同時拉股價 + USD/TWD 匯率。
    回傳 ({ticker: price_usd}, usd_twd_rate)
    """
    if not tickers:
        return {}, None
    try:
        import yfinance as yf

        all_symbols = tickers + ["TWD=X"]
        data = yf.Tickers(" ".join(all_symbols))

        prices: dict[str, float] = {}
        for t in tickers:
            try:
                price = data.tickers[t].fast_info.get("last_price") or data.tickers[t].fast_info.get("previousClose")
                if price:
                    prices[t] = float(price)
            except Exception:
                pass

        usd_twd: float | None = None
        try:
            fi = dict(data.tickers["TWD=X"].fast_info)
            # lastPrice = 當日延遲報價；fallback 到 previousClose
            rate = fi.get("lastPrice") or fi.get("previousClose")
            if rate:
                usd_twd = float(rate)
        except Exception:
            pass

        return prices, usd_twd
    except ImportError:
        return {}, None


def get_us_holdings() -> dict | None:
    """
    計算美股目前持倉，並用 yfinance 填入即時（延遲）報價與 USD/TWD 匯率。
    回傳格式：
      {
        "holdings": [{ ticker, name, shares, price_usd, market_value_usd, market_value_twd }, ...],
        "total_value_usd": float,
        "total_value_twd": float | None,
        "usd_twd_rate": float | None,
        "as_of": str,
        "price_source": "yfinance" | "unavailable"
      }
    """
    positions = _get_us_positions()
    if not positions:
        return None

    ticker_list = [p["ticker"] for p in positions]
    prices, usd_twd = _fetch_prices_and_rate(ticker_list)

    holdings = []
    total_usd = 0.0
    for pos in positions:
        t = pos["ticker"]
        shares = float(pos["total_shares"])
        price = prices.get(t)
        market_value_usd = shares * price if price else None
        market_value_twd = market_value_usd * usd_twd if (market_value_usd and usd_twd) else None
        if market_value_usd:
            total_usd += market_value_usd
        holdings.append({
            "ticker": t,
            "name": pos["name"] or t,
            "shares": shares,
            "price_usd": price,
            "market_value_usd": market_value_usd,
            "market_value_twd": market_value_twd,
        })

    total_twd = total_usd * usd_twd if (total_usd and usd_twd) else None

    return {
        "holdings": holdings,
        "total_value_usd": total_usd,
        "total_value_twd": total_twd,
        "usd_twd_rate": usd_twd,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "price_source": "yfinance" if prices else "unavailable",
    }


def import_baseline(positions: list[dict], trade_date: str) -> int:
    """
    匯入初始持股快照。
    positions: [{ "ticker": str, "name": str, "shares": float }]
    trade_date: "YYYY-MM-DD"
    回傳寫入筆數。
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute("DELETE FROM us_stock_transactions WHERE action = 'initial'")
        conn.executemany(
            """
            INSERT INTO us_stock_transactions (trade_date, ticker, name, action, shares, price, source_file, imported_at)
            VALUES (?, ?, ?, 'initial', ?, NULL, 'manual_baseline', ?)
            """,
            [(trade_date, p["ticker"], p.get("name", p["ticker"]), float(p["shares"]), now)
             for p in positions],
        )
    return len(positions)
