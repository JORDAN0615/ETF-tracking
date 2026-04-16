"""Statistics and analysis services for ETF tracking."""
from __future__ import annotations

from typing import Optional

from app.repositories import (
    get_diffs,
    get_latest_snapshot_date,
    get_snapshot,
    list_etfs,
)


def calculate_concentration_metrics(holdings: list[dict]) -> dict:
    """
    Calculate portfolio concentration metrics.
    
    Returns:
        dict with:
        - top10_weight: Sum of top 10 holdings weights
        - top5_weight: Sum of top 5 holdings weights
        - top3_weight: Sum of top 3 holdings weights
        - herfindahl_index: HHI (sum of squared weights)
        - effective_count: Effective number of holdings (1/HHI)
        - total_holdings: Total number of holdings
    """
    if not holdings:
        return {
            "top10_weight": 0,
            "top5_weight": 0,
            "top3_weight": 0,
            "herfindahl_index": 0,
            "effective_count": 0,
            "total_holdings": 0,
        }
    
    # Extract weights (handle None values)
    weights = [h.get("weight") for h in holdings if h.get("weight") is not None]
    weights = [w for w in weights if w is not None]
    
    if not weights:
        return {
            "top10_weight": 0,
            "top5_weight": 0,
            "top3_weight": 0,
            "herfindahl_index": 0,
            "effective_count": 0,
            "total_holdings": len(holdings),
        }
    
    # Sort by weight descending
    sorted_weights = sorted(weights, reverse=True)
    
    # Calculate top N weights
    top10_weight = sum(sorted_weights[:10]) if len(sorted_weights) >= 10 else sum(sorted_weights)
    top5_weight = sum(sorted_weights[:5]) if len(sorted_weights) >= 5 else sum(sorted_weights)
    top3_weight = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)
    
    # Calculate Herfindahl-Hirschman Index (HHI)
    # HHI = sum of squared weights (expressed as percentages)
    hhi = sum(w ** 2 for w in sorted_weights)
    
    # Effective number of holdings = 1 / HHI (when weights are proportions)
    # Since weights are percentages, we use: effective_count = 10000 / HHI
    effective_count = 10000 / hhi if hhi > 0 else 0
    
    return {
        "top10_weight": round(top10_weight, 2),
        "top5_weight": round(top5_weight, 2),
        "top3_weight": round(top3_weight, 2),
        "herfindahl_index": round(hhi, 2),
        "effective_count": round(effective_count, 2),
        "total_holdings": len(holdings),
    }


def calculate_turnover_metrics(diffs: list[dict]) -> dict:
    """
    Calculate portfolio turnover metrics.
    
    Returns:
        dict with:
        - total_changes: Total number of changes
        - new_entries: Number of new entries (enter_top10)
        - exits: Number of exits (exit_top10)
        - increases: Number of increases
        - decreases: Number of decreases
        - gross_turnover: Gross turnover rate
        - net_turnover: Net turnover rate
    """
    if not diffs:
        return {
            "total_changes": 0,
            "new_entries": 0,
            "exits": 0,
            "increases": 0,
            "decreases": 0,
            "gross_turnover": 0,
            "net_turnover": 0,
        }
    
    # Count by change type
    new_entries = sum(1 for d in diffs if d.get("change_type") == "enter_top10")
    exits = sum(1 for d in diffs if d.get("change_type") == "exit_top10")
    increases = sum(1 for d in diffs if d.get("change_type") == "increase")
    decreases = sum(1 for d in diffs if d.get("change_type") == "decrease")
    
    total_changes = len(diffs)
    
    # Calculate gross turnover (sum of absolute weight changes)
    gross_turnover = 0
    net_turnover = 0
    
    for diff in diffs:
        weight_delta = diff.get("weight_delta")
        if weight_delta is not None:
            gross_turnover += abs(weight_delta)
            net_turnover += weight_delta
    
    return {
        "total_changes": total_changes,
        "new_entries": new_entries,
        "exits": exits,
        "increases": increases,
        "decreases": decreases,
        "gross_turnover": round(gross_turnover, 2),
        "net_turnover": round(net_turnover, 2),
    }


def get_etf_statistics(ticker: str) -> dict:
    """
    Get comprehensive statistics for an ETF.
    
    Returns:
        dict with:
        - ticker: ETF ticker
        - latest_date: Latest snapshot date
        - concentration: Concentration metrics
        - turnover: Turnover metrics (from latest diff)
        - holding_count: Number of holdings
    """
    latest_date = get_latest_snapshot_date(ticker)
    
    if not latest_date:
        return {
            "ticker": ticker,
            "latest_date": None,
            "concentration": {},
            "turnover": {},
            "holding_count": 0,
        }
    
    # Get latest holdings and calculate concentration
    holdings = get_snapshot(ticker, latest_date)
    concentration = calculate_concentration_metrics(holdings)
    
    # Get latest diffs and calculate turnover
    diffs = get_diffs(ticker, latest_date)
    turnover = calculate_turnover_metrics(diffs)
    
    return {
        "ticker": ticker,
        "latest_date": latest_date,
        "concentration": concentration,
        "turnover": turnover,
        "holding_count": len(holdings),
    }


def get_all_etfs_statistics() -> list[dict]:
    """Get statistics for all ETFs."""
    etfs = list_etfs()
    return [get_etf_statistics(etf["ticker"]) for etf in etfs]


def get_common_holdings(min_etf_count: int = 2, top_n: int = 20) -> dict:
    """
    Get holdings that appear across multiple ETFs.

    Returns data pre-structured for a grouped bar chart:
    - tickers: list of ETF tickers that have snapshot data
    - ticker_names: {ticker: name}
    - common_holdings: instruments held by >= min_etf_count ETFs,
      sorted by (etf_count DESC, total_weight DESC), capped at top_n
    """
    from collections import Counter

    etfs = list_etfs()

    etf_snapshots: dict[str, dict[str, dict]] = {}
    for etf in etfs:
        if not etf.get("is_active"):
            continue
        ticker = etf["ticker"]
        latest_date = get_latest_snapshot_date(ticker)
        if not latest_date:
            continue
        holdings = get_snapshot(ticker, latest_date)
        etf_snapshots[ticker] = {h["instrument_key"]: h for h in holdings}

    if not etf_snapshots:
        return {"tickers": [], "ticker_names": {}, "common_holdings": []}

    tickers = list(etf_snapshots.keys())
    ticker_names = {etf["ticker"]: etf["name"] for etf in etfs}

    etf_count: Counter = Counter()
    for holdings in etf_snapshots.values():
        for key in holdings:
            etf_count[key] += 1

    common: list[dict] = []
    for key, count in etf_count.items():
        if count < min_etf_count:
            continue
        weights: dict[str, Optional[float]] = {}
        instrument_name = key
        for ticker in tickers:
            h = etf_snapshots[ticker].get(key)
            if h:
                instrument_name = h["instrument_name"]
                weights[ticker] = h.get("weight")
            else:
                weights[ticker] = None
        total_weight = sum(w for w in weights.values() if w is not None)
        common.append({
            "instrument_key": key,
            "instrument_name": instrument_name,
            "etf_count": count,
            "weights": weights,
            "total_weight": round(total_weight, 2),
        })

    common.sort(key=lambda x: (-x["etf_count"], -x["total_weight"]))

    return {
        "tickers": tickers,
        "ticker_names": {t: ticker_names.get(t, t) for t in tickers},
        "common_holdings": common[:top_n],
    }


def get_holding_history(
    ticker: str,
    instrument_key: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """
    Get historical holding data for trend analysis.
    
    Args:
        ticker: ETF ticker
        instrument_key: Optional specific instrument to track
        limit: Maximum number of snapshots to return
    
    Returns:
        List of historical holding records with trade_date, instrument info, quantity, weight
    """
    from app.repositories import get_connection, is_postgres
    
    query = """
        SELECT trade_date, instrument_key, instrument_name, instrument_type, quantity, weight
        FROM holdings_snapshots
        WHERE etf_ticker = ?
    """
    
    params = [ticker]
    
    if instrument_key:
        query += " AND instrument_key = ?"
        params.append(instrument_key)
    
    if is_postgres():
        query += " ORDER BY trade_date DESC, weight DESC LIMIT ?"
        params.append(limit)
    else:
        query += " ORDER BY trade_date DESC, weight DESC LIMIT ?"
        params.append(limit)
    
    with get_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    
    result = []
    for row in rows:
        result.append({
            "trade_date": row["trade_date"],
            "instrument_key": row["instrument_key"],
            "instrument_name": row["instrument_name"],
            "instrument_type": row["instrument_type"],
            "quantity": row["quantity"],
            "quantity_lots": row["quantity"] / 1000 if row["quantity"] else None,
            "weight": row["weight"],
        })
    
    return result


def get_weight_chart_data(ticker: str, limit: int = 30) -> dict:
    """
    Get structured chart data for weight trend and concentration analysis.

    Returns data pre-formatted for Chart.js:
    - dates: sorted list of trade dates (ascending)
    - top10_series: weight history per instrument (based on latest top-10)
    - concentration_series: top3/top5/top10 aggregate weights per date
    """
    from collections import defaultdict
    from app.repositories import get_connection

    # Step 1: Get the last `limit` distinct trade dates 拿最近 30 個交易日（trade_date） 
    with get_connection() as conn:
        date_rows = conn.execute(
            "SELECT DISTINCT trade_date FROM holdings_snapshots "
            "WHERE etf_ticker = ? ORDER BY trade_date DESC LIMIT ?",
            (ticker, limit),
        ).fetchall()

    if not date_rows:
        return {
            "dates": [],
            "top10_series": [],
            "concentration_series": {"top3": [], "top5": [], "top10": []},
        }

    # Sort dates ascending for chart display 排成升序
    dates = sorted(row["trade_date"] for row in date_rows)

    # Step 2: Fetch all holdings for those dates in one query
    placeholders = ",".join(["?"] * len(dates))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT trade_date, instrument_key, instrument_name, weight "
            f"FROM holdings_snapshots "
            f"WHERE etf_ticker = ? AND trade_date IN ({placeholders}) "
            f"ORDER BY trade_date ASC",
            tuple([ticker] + list(dates)),
        ).fetchall()

    # Step 3: Group by date
    holdings_by_date: dict = defaultdict(list)
    for row in rows:
        holdings_by_date[row["trade_date"]].append({
            "key": row["instrument_key"],
            "name": row["instrument_name"],
            "weight": row["weight"],
        })

    # Step 4: Determine top-10 instruments from the latest date
    latest_date = dates[-1]
    latest_sorted = sorted(
        [h for h in holdings_by_date.get(latest_date, []) if h["weight"] is not None],
        key=lambda h: h["weight"],
        reverse=True,
    )[:10]

    if not latest_sorted:
        return {
            "dates": dates,
            "top10_series": [],
            "concentration_series": {"top3": [], "top5": [], "top10": []},
        }

    top10_keys = [h["key"] for h in latest_sorted]
    key_to_name = {h["key"]: h["name"] for h in latest_sorted}

    # Step 5: Build per-instrument weight series (None if absent on a date)
    top10_series = []
    for key in top10_keys:
        weights = []
        for date in dates:
            match = next((h for h in holdings_by_date[date] if h["key"] == key), None)
            w = match["weight"] if match else None
            weights.append(round(w, 2) if w is not None else None)
        top10_series.append({"key": key, "name": key_to_name[key], "weights": weights})

    # Step 6: Build concentration series per date
    top3_list, top5_list, top10_list = [], [], []
    for date in dates:
        sorted_weights = sorted(
            [h["weight"] for h in holdings_by_date[date] if h["weight"] is not None],
            reverse=True,
        )
        top3_list.append(round(sum(sorted_weights[:3]), 2) if sorted_weights else None)
        top5_list.append(round(sum(sorted_weights[:5]), 2) if sorted_weights else None)
        top10_list.append(round(sum(sorted_weights[:10]), 2) if sorted_weights else None)

    return {
        "dates": dates,
        "top10_series": top10_series,
        "concentration_series": {"top3": top3_list, "top5": top5_list, "top10": top10_list},
    }


def get_weight_trend(
    ticker: str,
    instrument_key: str
) -> list[dict]:
    """
    Get weight trend for a specific instrument over time.
    
    Args:
        ticker: ETF ticker
        instrument_key: Instrument key (e.g., stock code)
    
    Returns:
        List of {trade_date, weight, quantity} sorted by date ascending
    """
    history = get_holding_history(ticker, instrument_key, limit=100)
    
    # Filter only records with weight data and sort by date ascending
    trend = [
        {
            "trade_date": h["trade_date"],
            "weight": h["weight"],
            "quantity": h["quantity"],
            "quantity_lots": h["quantity_lots"],
        }
        for h in history
        if h["weight"] is not None
    ]
    
    # Sort by date ascending
    trend.sort(key=lambda x: x["trade_date"])
    
    return trend
