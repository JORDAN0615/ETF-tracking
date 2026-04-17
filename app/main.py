from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import init_db
from app.repositories import (
    get_diffs,
    get_etf,
    get_latest_crawl_run,
    get_snapshot,
    get_snapshot_metadata,
    get_latest_snapshot_metadata,
    list_etfs,
    remove_etf,
    seed_default_data,
)
from app.services.ingest import ingest_latest_snapshot, refresh_active_etfs
from app.services.maintenance import lock_00992a_baseline
from app.services.portfolio import get_latest_holdings
from app.services.cathay_sync import run as run_cathay_sync
from app.services.us_portfolio import get_us_holdings, import_baseline
from app.services.us_stock_sync import run as run_us_stock_sync
from app.services.firstrade_sync import run as run_firstrade_sync
from app.services.export import (
    export_diffs_csv,
    export_diffs_json,
    export_etf_summary_json,
    export_holdings_csv,
    export_holdings_json,
    export_statistics_json,
)
from app.services.notifications import create_telegram_notifier
from app.services.statistics import (
    get_etf_statistics,
    get_all_etfs_statistics,
    get_common_holdings,
    get_holding_history,
    get_weight_chart_data,
    get_weight_trend,
)


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def _format_datetime(value: Optional[str], include_date: bool = True) -> Optional[str]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if include_date:
        return parsed.strftime("%Y-%m-%d %H:%M")
    return parsed.strftime("%H:%M")


def _format_lots(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


templates.env.filters["format_lots"] = _format_lots


def _diff_weight_value(diff: dict) -> float:
    if diff.get("curr_weight") is not None:
        return float(diff["curr_weight"])
    if diff.get("prev_weight") is not None:
        return float(diff["prev_weight"])
    return -1.0


def _top_weight_diffs(diffs: list[dict], limit: int = 10) -> list[dict]:
    ranked = sorted(
        diffs,
        key=lambda item: (
            _diff_weight_value(item),
            abs(item.get("quantity_delta_lots") or 0.0),
            item.get("instrument_key", ""),
        ),
        reverse=True,
    )
    return ranked[:limit]


async def _scheduler_loop() -> None:
    while True:
        now = datetime.now(TAIPEI_TZ)
        next_run = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())
        await asyncio.to_thread(_run_scheduled_refresh_with_retry)


def _run_scheduled_refresh_with_retry() -> None:
    before_dates = {
        etf["ticker"]: etf.get("latest_trade_date")
        for etf in list_etfs()
        if etf.get("is_active")
    }
    first_pass = refresh_active_etfs("scheduled", trust_today=True)
    retry_candidates: list[str] = []
    for result in first_pass.get("results", []):
        ticker = result.get("ticker")
        if not ticker:
            continue
        previous_date = before_dates.get(ticker)
        current_date = result.get("trade_date")
        status = result.get("status")
        # Retry once when refresh failed or trade_date did not move forward.
        if status != "success" or current_date is None or current_date == previous_date:
            retry_candidates.append(ticker)

    if not retry_candidates:
        return

    retry_delay_seconds = int(os.getenv("ETF_TRACKING_SCHEDULE_RETRY_DELAY_SECONDS", "1800"))
    if retry_delay_seconds > 0:
        # Sleep in the scheduler worker thread before a single retry pass.
        import time

        time.sleep(retry_delay_seconds)

    for ticker in retry_candidates:
        ingest_latest_snapshot(ticker, trigger_type="scheduled_retry", trust_today=True)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    init_db()
    remove_etf("00994A")
    seed_default_data()
    lock_00992a_baseline()
    scheduler_task = None
    scheduler_disabled = os.getenv("ETF_TRACKING_DISABLE_SCHEDULER") == "1" or os.getenv("VERCEL") == "1"
    if not scheduler_disabled:
        scheduler_task = asyncio.create_task(_scheduler_loop())
        app_instance.state.scheduler_task = scheduler_task
    try:
        yield
    finally:
        if scheduler_task:
            scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler_task


app = FastAPI(
    title="Taiwan Active ETF Tracker",
    description="追蹤台灣主動式 ETF 持股變動的 API 系統",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/etfs")
def get_etfs() -> list[dict]:
    return list_etfs()


@app.get("/etfs/common-holdings")
def get_common_holdings_endpoint(
    min_etf_count: int = Query(2, ge=2, le=5, description="Minimum ETFs holding the instrument"),
    top_n: int = Query(20, ge=5, le=50, description="Maximum instruments to return"),
) -> dict:
    """Get holdings that appear across multiple ETFs, structured for chart rendering."""
    return get_common_holdings(min_etf_count=min_etf_count, top_n=top_n)


@app.post("/etfs/{ticker}/fetch")
def fetch_latest_snapshot(ticker: str, target_date: Optional[str] = None) -> dict:
    try:
        result = ingest_latest_snapshot(ticker, target_date=target_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if result["status"] != "success":
        raise HTTPException(status_code=502, detail=result)
    return result


@app.post("/etfs/{ticker}/refresh")
def refresh_single_etf(ticker: str, target_date: Optional[str] = None) -> RedirectResponse:
    ingest_latest_snapshot(ticker, target_date=target_date)
    return RedirectResponse(url=f"/etfs/{ticker}", status_code=303)


@app.post("/refresh")
def refresh_all() -> RedirectResponse:
    refresh_active_etfs()
    return RedirectResponse(url="/", status_code=303)


@app.get("/etfs/{ticker}/holdings")
def get_holdings(ticker: str, date: str = Query(..., alias="date")) -> dict:
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    metadata = get_snapshot_metadata(ticker, date)
    holdings = get_snapshot(ticker, date)
    for row in holdings:
        row["quantity_lots"] = row["quantity"] / 1000 if row["quantity"] is not None else None
    return {
        "ticker": ticker,
        "trade_date": date,
        "fetched_at": metadata["fetched_at"] if metadata else None,
        "holdings": holdings,
    }


@app.get("/etfs/{ticker}/diffs")
def get_holding_diffs(ticker: str, date: str = Query(..., alias="date")) -> dict:
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    return {"ticker": ticker, "trade_date": date, "diffs": get_diffs(ticker, date)}


def _build_card(etf_item: dict, today: str) -> dict:
    metadata = get_latest_snapshot_metadata(etf_item["ticker"])
    latest_date = metadata["trade_date"] if metadata else None
    latest_fetched_at = metadata["fetched_at"] if metadata else None
    latest_run = get_latest_crawl_run(etf_item["ticker"])
    diffs = get_diffs(etf_item["ticker"], latest_date) if latest_date else []
    display_diffs = _top_weight_diffs(diffs, limit=10)
    grouped = {
        "enter_top10": [diff for diff in display_diffs if diff["change_type"] == "enter_top10"],
        "increase": [diff for diff in display_diffs if diff["change_type"] == "increase"],
        "decrease": [diff for diff in display_diffs if diff["change_type"] == "decrease"],
        "exit_top10": [diff for diff in display_diffs if diff["change_type"] == "exit_top10"],
    }
    return {
        "etf": get_etf(etf_item["ticker"]),
        "latest_date": latest_date,
        "latest_fetched_at": latest_fetched_at,
        "latest_fetched_at_display": _format_datetime(latest_fetched_at),
        "is_stale": bool(latest_date and latest_date != today),
        "display_diffs": display_diffs,
        "grouped_diffs": grouped,
        "summary": {key: len(value) for key, value in grouped.items()},
        "last_run_status": latest_run["status"] if latest_run else None,
        "last_run_finished_at": latest_run["finished_at"] if latest_run else None,
        "last_run_finished_at_display": _format_datetime(
            latest_run["finished_at"], include_date=False
        )
        if latest_run
        else None,
        "last_run_error": latest_run["error_message"] if latest_run else None,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    etfs = list_etfs()
    if not etfs:
        raise HTTPException(status_code=404, detail="No ETF configured")

    today = datetime.now().date().isoformat()
    cards = [_build_card(etf_item, today) for etf_item in etfs]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "cards": cards,
            "active": "etf",
        },
    )


@app.get("/portfolio", response_class=HTMLResponse)
def portfolio_page(request: Request) -> HTMLResponse:
    data = get_latest_holdings()
    if not data:
        raise HTTPException(status_code=404, detail="No portfolio data found")
    
    return templates.TemplateResponse(
        request,
        "portfolio.html",
        {
            "data": data,
            "active": "portfolio",
        },
    )


@app.get("/portfolio/holdings")
def portfolio_holdings() -> dict:
    data = get_latest_holdings()
    if not data:
        raise HTTPException(status_code=404, detail="No portfolio data found")
    return data


@app.post("/portfolio/sync")
def portfolio_sync():
    try:
        run_cathay_sync()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── US Stock Portfolio ────────────────────────────────────────────────────────

@app.get("/us-portfolio/holdings")
def us_portfolio_holdings() -> dict:
    data = get_us_holdings()
    if not data:
        raise HTTPException(status_code=404, detail="No US stock positions found. Import baseline first.")
    return data


@app.post("/us-portfolio/baseline")
def us_portfolio_baseline(positions: list[dict]) -> dict:
    """
    匯入美股初始持倉。
    Body: [{ "ticker": "AAPL", "name": "Apple Inc.", "shares": 10.5 }, ...]
    """
    if not positions:
        raise HTTPException(status_code=400, detail="positions list is empty")
    today = datetime.now().date().isoformat()
    try:
        count = import_baseline(positions, today)
        return {"status": "ok", "imported": count, "trade_date": today}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/us-portfolio/sync")
def us_portfolio_sync() -> dict:
    """從 Gmail 抓取最新客戶日買賣報告書並匯入交易紀錄。"""
    try:
        return run_us_stock_sync()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/us-portfolio/firstrade-sync")
def us_portfolio_firstrade_sync() -> dict:
    """從 Firstrade API 同步最新持倉。"""
    try:
        return run_firstrade_sync()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/us-portfolio/sync-all")
def us_portfolio_sync_all() -> dict:
    """同時觸發國泰 + Firstrade 同步。"""
    cathay_result = run_us_stock_sync()
    firstrade_result = run_firstrade_sync()
    return {
        "status": "ok",
        "cathay": cathay_result,
        "firstrade": firstrade_result,
        "synced_at": datetime.now().isoformat(),
    }


@app.get("/etfs/{ticker}", response_class=HTMLResponse)
def etf_detail(request: Request, ticker: str) -> HTMLResponse:
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")

    today = datetime.now().date().isoformat()
    card = _build_card(etf, today)
    snapshot = get_snapshot(ticker, card["latest_date"]) if card.get("latest_date") else []
    return templates.TemplateResponse(
        request,
        "detail.html",
        {
            "card": card,
            "diffs": card["display_diffs"],
            "snapshot": snapshot,
            "active": "etf",
        },
    )


# ============================================================================
# Enhanced API Endpoints - Statistics & Analysis
# ============================================================================

@app.get("/etfs/{ticker}/statistics")
def get_statistics(ticker: str) -> dict:
    """Get statistics for an ETF (concentration, turnover metrics)."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    return get_etf_statistics(ticker)


@app.get("/etfs/statistics")
def get_all_statistics() -> list[dict]:
    """Get statistics for all ETFs."""
    return get_all_etfs_statistics()


@app.get("/etfs/{ticker}/history")
def get_history(
    ticker: str,
    instrument_key: Optional[str] = Query(None, description="Filter by specific instrument"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records")
) -> dict:
    """Get historical holding data for trend analysis."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    history = get_holding_history(ticker, instrument_key=instrument_key, limit=limit)
    return {
        "ticker": ticker,
        "instrument_key": instrument_key,
        "history": history,
    }


@app.get("/etfs/{ticker}/chart-data")
def get_chart_data(
    ticker: str,
    limit: int = Query(30, ge=5, le=60, description="Number of recent trading days"),
) -> dict:
    """Get pre-structured chart data for weight trend and concentration analysis."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    return get_weight_chart_data(ticker, limit)


@app.get("/etfs/{ticker}/trend/{instrument_key}")
def get_trend(ticker: str, instrument_key: str) -> dict:
    """Get weight trend for a specific instrument over time."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    trend = get_weight_trend(ticker, instrument_key)
    return {
        "ticker": ticker,
        "instrument_key": instrument_key,
        "trend": trend,
    }


# ============================================================================
# Export API Endpoints
# ============================================================================

@app.get("/etfs/{ticker}/holdings/export/csv")
def export_holdings_as_csv(ticker: str, date: str = Query(..., alias="date")):
    """Export holdings as CSV file."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    holdings = get_snapshot(ticker, date)
    if not holdings:
        raise HTTPException(status_code=404, detail=f"No holdings found for {ticker} on {date}")
    
    return export_holdings_csv(holdings)


@app.get("/etfs/{ticker}/holdings/export/json")
def export_holdings_as_json(ticker: str, date: str = Query(..., alias="date")):
    """Export holdings as JSON file."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    holdings = get_snapshot(ticker, date)
    if not holdings:
        raise HTTPException(status_code=404, detail=f"No holdings found for {ticker} on {date}")
    
    return export_holdings_json(holdings)


@app.get("/etfs/{ticker}/diffs/export/csv")
def export_diffs_as_csv(ticker: str, date: str = Query(..., alias="date")):
    """Export holding diffs as CSV file."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    diffs = get_diffs(ticker, date)
    return export_diffs_csv(diffs)


@app.get("/etfs/{ticker}/diffs/export/json")
def export_diffs_as_json(ticker: str, date: str = Query(..., alias="date")):
    """Export holding diffs as JSON file."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    diffs = get_diffs(ticker, date)
    return export_diffs_json(diffs)


@app.get("/etfs/export/json")
def export_all_etfs_json():
    """Export all ETF summary as JSON file."""
    etfs = list_etfs()
    return export_etf_summary_json(etfs)


@app.get("/etfs/{ticker}/statistics/export/json")
def export_statistics_as_json(ticker: str):
    """Export ETF statistics as JSON file."""
    etf = get_etf(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"Unknown ETF ticker: {ticker}")
    
    stats = get_etf_statistics(ticker)
    return export_statistics_json(stats)


# New endpoint: GET /etfs/test-parallel

@app.get('/etfs/test-parallel')
def test_parallel() -> dict:
    """Test parallel development endpoint."""
    return {'status': 'ok', 'parallel': True}

