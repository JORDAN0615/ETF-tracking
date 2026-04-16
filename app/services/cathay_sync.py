"""
cathay_sync.py — 國泰對帳單同步服務

流程：Gmail IMAP → 下載 PDF → 解密解析持倉 → upsert my_holdings
"""

import imaplib
import email
import re
import os
import sqlite3
from datetime import datetime, timezone
from email.header import decode_header
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
PDF_PASSWORD = os.getenv("CATHAY_PDF_PASSWORD")

_BASE = os.path.join(os.path.dirname(__file__), "..", "..")
DB_PATH = os.path.normpath(os.path.join(_BASE, "data", "etf_tracking.db"))
SAVE_DIR = os.path.normpath(os.path.join(_BASE, "data", "raw_pdfs"))

SUBJECT_TEXT = "國泰綜合證券日對帳單"


# ── Gmail ─────────────────────────────────────────────────────────────────────

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
    return None


def fetch_latest_pdf() -> tuple[str, str] | None:
    """下載最新一封對帳單 PDF，回傳 (本地路徑, 原始檔名)。找不到回傳 None。"""
    print(f"Connecting to Gmail ({GMAIL_USER})...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASSWORD)

    folder = _find_all_mail_folder(mail)
    if not folder:
        print("ERROR: Cannot find All Mail folder.")
        return None

    mail.select(f'"{folder}"')
    status, messages = mail.search(None, "ALL")
    all_ids = messages[0].split()
    if not all_ids:
        return None

    found_id = None
    for mid in reversed(all_ids[-200:]):
        status, data = mail.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT)])")
        for resp in data:
            if isinstance(resp, tuple):
                subject = _decode_mime_str(
                    resp[1].decode("utf-8", errors="replace")
                    .replace("Subject:", "").strip()
                )
                if SUBJECT_TEXT in subject:
                    found_id = mid
                    break
        if found_id:
            break

    if not found_id:
        print("No matching email found.")
        return None

    print(f"Found email (ID: {found_id.decode()}). Downloading PDF...")
    status, data = mail.fetch(found_id, "(RFC822)")
    mail.close()
    mail.logout()

    for resp in data:
        if not isinstance(resp, tuple):
            continue
        msg = email.message_from_bytes(resp[1])
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue
            raw_fn = part.get_filename()
            if not raw_fn:
                continue
            filename = _decode_mime_str(raw_fn)
            if not filename.lower().endswith(".pdf"):
                continue

            os.makedirs(SAVE_DIR, exist_ok=True)
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(part.get_payload(decode=True))
            print(f"Saved: {filepath}")
            return filepath, filename

    return None


# ── PDF Parser ────────────────────────────────────────────────────────────────

def _parse_roc_date(text: str) -> str | None:
    """「115 年 4月 15 日」→ 2026-04-15"""
    m = re.search(r"(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", text)
    if not m:
        return None
    year = int(m.group(1)) + 1911
    return f"{year}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def parse_holdings(pdf_path: str) -> tuple[str, list[dict]]:
    """
    解密並解析 PDF。
    回傳 (trade_date, holdings)
    holdings: [{ticker, name, close_price, shares, market_value}, ...]
    """
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        reader.decrypt(PDF_PASSWORD)

    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    trade_date = _parse_roc_date(full_text)
    if not trade_date:
        m = re.search(r"(\d{4}/\d{2}/\d{2})", full_text)
        trade_date = m.group(1).replace("/", "-") if m else datetime.now().strftime("%Y-%m-%d")

    section_match = re.search(
        r"代碼\s+股票名稱.+?\n(.+?)集保市值總計",
        full_text,
        re.DOTALL,
    )
    if not section_match:
        print("WARNING: Cannot find holdings section in PDF.")
        return trade_date, []

    holdings = []
    pattern = re.compile(
        r"^(\S+)\s+(.+?)\s+[▲▼]([\d,]+\.?\d*)\s+([\d,]+)\s+([\d,]+\.?\d*)\s+\d+\s+\d+",
        re.MULTILINE,
    )
    for m in pattern.finditer(section_match.group(1)):
        holdings.append({
            "ticker": m.group(1).strip(),
            "name": m.group(2).strip(),
            "close_price": float(m.group(3).replace(",", "")),
            "shares": int(m.group(4).replace(",", "")),
            "market_value": float(m.group(5).replace(",", "")),
        })

    return trade_date, holdings


# ── DB ────────────────────────────────────────────────────────────────────────

def upsert_holdings(trade_date: str, holdings: list[dict], source_file: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for h in holdings:
        cur.execute(
            """
            INSERT INTO my_holdings
                (trade_date, ticker, name, close_price, shares, market_value, source_file, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date, ticker) DO UPDATE SET
                name=excluded.name,
                close_price=excluded.close_price,
                shares=excluded.shares,
                market_value=excluded.market_value,
                source_file=excluded.source_file,
                imported_at=excluded.imported_at
            """,
            (trade_date, h["ticker"], h["name"], h["close_price"],
             h["shares"], h["market_value"], source_file, now),
        )
    conn.commit()
    conn.close()
    print(f"Upserted {len(holdings)} rows for {trade_date}.")


# ── Public API ────────────────────────────────────────────────────────────────

def run():
    """完整執行一次同步流程"""
    result = fetch_latest_pdf()
    if not result:
        print("No PDF downloaded. Exiting.")
        return

    pdf_path, filename = result
    trade_date, holdings = parse_holdings(pdf_path)

    if not holdings:
        print("No holdings parsed.")
        return

    print(f"\nTrade date: {trade_date}")
    print(f"Holdings ({len(holdings)}):")
    for h in holdings:
        print(f"  {h['ticker']:8s} {h['name']:12s} {h['shares']:>6} 股  "
              f"@{h['close_price']:>8.2f}  市值 {h['market_value']:>10,.1f}")

    upsert_holdings(trade_date, holdings, filename)
    print("\nDone.")
