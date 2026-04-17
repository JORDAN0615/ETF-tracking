"""
us_stock_sync.py — 國泰附委托客戶日買賣報告書同步

流程：Gmail IMAP → 下載 PDF → 解密解析交易紀錄 → 寫入 us_stock_transactions
"""
from __future__ import annotations

import imaplib
import email
import io
import os
import re
from datetime import datetime, timezone
from email.header import decode_header

from dotenv import load_dotenv
from pypdf import PdfReader

from app.db import get_connection

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
PDF_PASSWORD = os.getenv("CATHAY_PDF_PASSWORD")

SUBJECT_KEYWORD = "國泰綜合證券客戶買賣報告書"  # 完整主旨含後綴 "Cathay Securities Trade Confirmation"


# ── Gmail helpers（與 cathay_sync.py 相同邏輯）──────────────────────────────────

def _decode_mime_str(raw: str) -> str:
    parts = decode_header(raw)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result


def _find_all_mail_folder(mail: imaplib.IMAP4_SSL) -> str | None:
    status, folders = mail.list()
    if status != "OK":
        return None
    for f in folders:
        raw = f.decode("utf-8", errors="replace")
        if "\\All" in raw:
            m = re.search(r'"([^"]+)"\s*$', raw)
            if m:
                return m.group(1)
            m = re.search(r'\s(\S+)\s*$', raw)
            if m:
                return m.group(1)
    return None


def _fetch_latest_pdf(subject_keyword: str) -> tuple[bytes, str] | None:
    """
    搜尋 Gmail 最近 200 封信，找主旨含 subject_keyword 的最新一封。
    回傳 (pdf_bytes, filename) 或 None。
    """
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASSWORD)

    folder = _find_all_mail_folder(mail)
    if not folder:
        mail.logout()
        raise RuntimeError("找不到 Gmail \\All 資料夾")

    mail.select(f'"{folder}"', readonly=True)
    status, data = mail.search(None, "ALL")
    if status != "OK":
        mail.logout()
        return None

    all_ids = data[0].split()
    recent_ids = all_ids[-200:]

    matched = None
    for uid in reversed(recent_ids):
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subject = _decode_mime_str(msg.get("Subject", ""))
        if subject_keyword not in subject:
            continue

        # 找 PDF 附件
        for part in msg.walk():
            if part.get_content_type() != "application/pdf":
                continue
            filename = _decode_mime_str(part.get_filename() or "report.pdf")
            pdf_bytes = part.get_payload(decode=True)
            if pdf_bytes:
                matched = (pdf_bytes, filename)
                break
        if matched:
            break

    mail.logout()
    return matched


# ── PDF 解析 ───────────────────────────────────────────────────────────────────

def _extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if reader.is_encrypted:
        reader.decrypt(PDF_PASSWORD)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_trade_date(text: str) -> str:
    """
    從 PDF 文字中擷取交易日期。
    格式：「2026年04月15日」→「2026-04-15」
    """
    m = re.search(r'(\d{4})年(\d{2})月(\d{2})日', text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return datetime.now().date().isoformat()


def _parse_transactions(text: str) -> list[dict]:
    """
    從 PDF 文字解析買賣交易明細。

    國泰客戶日買賣報告書格式（pypdf 解析後每欄一行）：
      00003725 AAOI/Applied Optoelectronic
      美國 賣出
      USD
      1.000000         ← 股數
      141.340000000    ← 價格
      ...
    """
    pattern = re.compile(
        r'\d{8}\s+([A-Z0-9.]+)/([^\n]+)\n'  # ref  TICKER/名稱
        r'美國\s+(買進|賣出)\n'               # 市場 + 買賣別
        r'USD\n'                              # 幣別
        r'([\d.]+)\n'                         # 股數
        r'([\d.]+)',                          # 價格
        re.MULTILINE,
    )
    transactions = []
    for m in pattern.finditer(text):
        transactions.append({
            "ticker": m.group(1).strip(),
            "name":   m.group(2).strip(),
            "action": "buy" if "買" in m.group(3) else "sell",
            "shares": float(m.group(4)),
            "price":  float(m.group(5)),
        })
    return transactions


# ── DB 寫入 ───────────────────────────────────────────────────────────────────

def _already_imported(source_file: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM us_stock_transactions WHERE source_file = ? LIMIT 1",
            (source_file,),
        ).fetchone()
    return row is not None


def _get_watermark_date() -> str | None:
    """回傳 DB 目前最新的交易日（即 baseline 或上一筆成功匯入的日期）。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(trade_date) FROM us_stock_transactions"
        ).fetchone()
    return row[0] if row else None


def _insert_transactions(trade_date: str, transactions: list[dict], source_file: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (trade_date, t["ticker"], t.get("name"), t["action"],
         t["shares"], t.get("price"), source_file, now)
        for t in transactions
    ]
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO us_stock_transactions
                (trade_date, ticker, name, action, shares, price, source_file, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


# ── 公開入口 ───────────────────────────────────────────────────────────────────

def run() -> dict:
    """
    抓取最新客戶日買賣報告書並寫入 DB。
    回傳 { "status": "ok"|"skipped"|"error", "imported": int, "message": str }
    """
    result = _fetch_latest_pdf(SUBJECT_KEYWORD)
    if not result:
        return {"status": "skipped", "imported": 0, "message": "找不到符合主旨的信件"}

    pdf_bytes, filename = result

    if _already_imported(filename):
        return {"status": "skipped", "imported": 0, "message": f"已匯入過：{filename}"}

    text = _extract_text(pdf_bytes)
    trade_date = _parse_trade_date(text)

    # 日期 watermark 檢查：PDF 的交易日必須晚於 DB 目前最新日
    watermark = _get_watermark_date()
    if watermark and trade_date <= watermark:
        return {
            "status": "skipped",
            "imported": 0,
            "message": f"PDF 交易日 {trade_date} ≤ DB 最新日 {watermark}，跳過以防重複計算",
        }

    transactions = _parse_transactions(text)

    if not transactions:
        # PDF 解析正則尚未實作 / 格式不符
        return {
            "status": "skipped",
            "imported": 0,
            "message": f"PDF 解析到 0 筆交易（{filename}）。請確認 PDF 格式並調整正則。",
            "pdf_text_preview": text[:500],
        }

    count = _insert_transactions(trade_date, transactions, filename)
    return {"status": "ok", "imported": count, "message": f"成功匯入 {count} 筆（{filename}）"}
