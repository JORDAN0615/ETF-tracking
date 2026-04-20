"""
firstrade_sync.py — Firstrade 持倉同步

流程：Firstrade API → get_positions() → 寫入 us_stock_transactions（broker='firstrade'）
採快照模式：每次同步先刪除舊的 firstrade 紀錄，再寫入最新持倉。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from firstrade import account

from app.db import get_connection

load_dotenv()

FIRSTRADE_USERNAME = os.getenv("FIRSTRADE_USERNAME")
FIRSTRADE_PASSWORD = os.getenv("FIRSTRADE_PASSWORD")
FIRSTRADE_EMAIL = os.getenv("FIRSTRADE_GMAIL_USER")


def _login() -> account.FTAccountData:
    session = account.FTSession(
        username=FIRSTRADE_USERNAME,
        password=FIRSTRADE_PASSWORD,
        email=FIRSTRADE_EMAIL,
    )
    need_code = session.login()
    if need_code:
        raise RuntimeError("Firstrade 要求 OTP 認證，目前不支援自動處理，請稍後再試")
    return account.FTAccountData(session)


def _fetch_all_positions(ft: account.FTAccountData) -> list[dict]:
    """取得所有帳戶的持倉，合併回傳"""
    all_items = []
    for acct in ft.account_numbers:
        pos = ft.get_positions(acct)
        items = pos.get("items", [])
        all_items.extend(items)
    return all_items


def _upsert_positions(items: list[dict]) -> int:
    """先清除舊快照，再寫入最新持倉。回傳寫入筆數。"""
    if not items:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    trade_date = datetime.now().date().isoformat()

    rows = [
        (
            trade_date,
            item["symbol"],
            item.get("company_name") or item["symbol"],
            "buy",
            float(item["quantity"]),
            float(item.get("last") or 0) or None,
            "firstrade_api",
            now,
            "firstrade",
            float(item["unit_cost"]) if item.get("unit_cost") else None,
        )
        for item in items
        if float(item.get("quantity", 0)) > 0
    ]

    with get_connection() as conn:
        conn.execute(
            "DELETE FROM us_stock_transactions WHERE broker = 'firstrade'"
        )
        conn.executemany(
            """
            INSERT INTO us_stock_transactions
                (trade_date, ticker, name, action, shares, price, source_file, imported_at, broker, cost_basis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def run() -> dict:
    """
    同步 Firstrade 持倉到 DB。
    回傳 { "status": "ok"|"error", "imported": int, "message": str }
    """
    try:
        ft = _login()
        items = _fetch_all_positions(ft)
        count = _upsert_positions(items)
        return {
            "status": "ok",
            "imported": count,
            "message": f"Firstrade 同步成功，{count} 筆持倉",
        }
    except Exception as e:
        return {
            "status": "error",
            "imported": 0,
            "message": str(e),
        }
