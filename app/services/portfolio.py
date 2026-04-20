import sqlite3
import os
import urllib.request
import json

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "etf_tracking.db"))


def _fetch_tw_live_prices(tickers: list[str]) -> dict[str, float]:
    """
    用 twstock 取得台股即時報價（盤中即時，無延遲）。
    支援上市 (tse) 和上櫃 (tpex)。

    回傳 {ticker: price}，抓不到的 ticker 不在 dict 裡。
    """
    try:
        import twstock
    except ImportError:
        return {}

    prices = {}
    for ticker in tickers:
        try:
            s = twstock.realtime.get(ticker)
            if not s.get('success'):
                continue
            r = s.get('realtime', {})
            price_str = r.get('latest_trade_price', '')

            # latest_trade_price 是 '-' 時（未成交），用最佳買價 best_bid_price[1]
            if price_str == '-' or price_str == '':
                bp = r.get('best_bid_price', [])
                if len(bp) > 1:
                    price_str = bp[1]

            if price_str and price_str != '-':
                price = float(price_str)
                if price > 0:
                    prices[ticker] = price
        except Exception:
            continue

    return prices


def _fetch_yf_tw_prices(tickers: list[str]) -> dict[str, float]:
    """yfinance fallback：拉台股前一交易日收盤價。"""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    prices = {}
    for ticker in tickers:
        if ticker in prices:
            continue
        for suffix in [".TW", ".TWO"]:
            try:
                fi = dict(yf.Ticker(ticker + suffix).fast_info)
                price = fi.get("lastPrice") or fi.get("previousClose")
                if price and float(price) > 0:
                    prices[ticker] = float(price)
                    break
            except Exception:
                continue
    return prices


def get_latest_holdings():
    """
    Fetch the most recent portfolio snapshot from my_holdings,
    merged with tw_manual_positions (other brokers),
    with avg_cost from tw_stock_cost_basis for P&L calculation.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT trade_date FROM my_holdings ORDER BY trade_date DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    latest_date = row['trade_date']

    # 國泰持倉（PDF 快照）
    cursor.execute(
        "SELECT ticker, name, shares, close_price, market_value FROM my_holdings WHERE trade_date = ?",
        (latest_date,),
    )
    cathay_rows = {r['ticker']: dict(r) for r in cursor.fetchall()}

    # 手動持倉（其他券商）
    cursor.execute("SELECT ticker, name, broker, shares, avg_cost FROM tw_manual_positions")
    manual_rows = cursor.fetchall()

    # 成本均價設定（國泰帳戶）
    cursor.execute("SELECT ticker, avg_cost FROM tw_stock_cost_basis")
    cost_map = {r['ticker']: r['avg_cost'] for r in cursor.fetchall()}

    conn.close()

    # 合併：以 ticker 為 key，累計股數與成本
    merged: dict[str, dict] = {}

    for ticker, r in cathay_rows.items():
        merged[ticker] = {
            "ticker": ticker,
            "name": r['name'],
            "close_price": r['close_price'],
            "total_shares": float(r['shares']),
            "total_cost": float(r['shares']) * cost_map.get(ticker, 0) if cost_map.get(ticker) else None,
            "has_cost": ticker in cost_map,
        }

    for r in manual_rows:
        ticker = r['ticker']
        manual_cost = float(r['shares']) * float(r['avg_cost'])
        if ticker in merged:
            merged[ticker]['total_shares'] += float(r['shares'])
            if merged[ticker]['total_cost'] is not None:
                merged[ticker]['total_cost'] += manual_cost
            else:
                merged[ticker]['total_cost'] = manual_cost
            merged[ticker]['has_cost'] = True
        else:
            # 純手動持倉（不在 PDF 裡），需要 close_price
            close = cathay_rows.get(ticker, {}).get('close_price', 0)
            merged[ticker] = {
                "ticker": ticker,
                "name": r['name'],
                "close_price": close,
                "total_shares": float(r['shares']),
                "total_cost": manual_cost,
                "has_cost": True,
            }

    # 用 twstock 即時報價，若失敗則 fallback 到 yfinance（收盤價）
    all_tickers = list(merged.keys())
    tw_prices = _fetch_tw_live_prices(all_tickers)
    yf_prices = _fetch_yf_tw_prices(all_tickers)

    holdings = []
    total_value = 0
    for ticker, m in sorted(merged.items()):
        shares = m['total_shares']
        # 優先用 twstock 即時價 → yfinance 延遲價 → PDF 舊收盤價
        if ticker in tw_prices:
            close_price = tw_prices[ticker]
            price_source = "live"
        elif ticker in yf_prices:
            close_price = yf_prices[ticker]
            price_source = "yfinance"
        else:
            close_price = m['close_price']
            price_source = "pdf"
        market_value = shares * close_price

        avg_cost = None
        unrealized_pnl = None
        unrealized_pnl_pct = None
        if m['has_cost'] and m['total_cost'] and shares > 0:
            avg_cost = m['total_cost'] / shares
            unrealized_pnl = (close_price - avg_cost) * shares
            unrealized_pnl_pct = (close_price / avg_cost - 1) * 100

        holdings.append({
            "ticker": ticker,
            "name": m['name'],
            "shares": shares,
            "close_price": close_price,
            "market_value": market_value,
            "avg_cost": avg_cost,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "price_source": price_source,
        })
        total_value += market_value

    # 計算總成本（台股）
    total_cost = sum(
        (m['total_cost'] or 0)
        for m in merged.values()
        if m['has_cost'] and m['total_cost']
    )

    return {
        "trade_date": latest_date,
        "holdings": holdings,
        "total_value": total_value,
        "total_cost": total_cost,
    }


def set_manual_position(ticker: str, name: str, broker: str, shares: float, avg_cost: float) -> None:
    """新增或更新手動持倉（其他券商）。"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO tw_manual_positions (ticker, name, broker, shares, avg_cost, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, broker) DO UPDATE SET
            name=excluded.name, shares=excluded.shares,
            avg_cost=excluded.avg_cost, updated_at=excluded.updated_at
        """,
        (ticker, name, broker, shares, avg_cost, now),
    )
    conn.commit()
    conn.close()


def set_cost_basis(positions: list[dict]) -> int:
    """
    手動設定台股成本均價。
    positions: [{ "ticker": str, "avg_cost": float }, ...]
    回傳更新筆數。
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        """
        INSERT INTO tw_stock_cost_basis (ticker, avg_cost, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET avg_cost=excluded.avg_cost, updated_at=excluded.updated_at
        """,
        [(p["ticker"], float(p["avg_cost"]), now) for p in positions],
    )
    conn.commit()
    conn.close()
    return len(positions)
