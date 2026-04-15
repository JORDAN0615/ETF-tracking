# ETF Tracking System 程式碼品質審查報告

## 執行摘要

本專案整體架構清晰，採用 FastAPI + SQLite/PostgreSQL 的組合，並實作適配器模式來處理不同投信網站的資料抓取。程式碼品質中等，有若干改進空間，特別是在型別提示、程式碼重複和錯誤處理方面。

---

## 1. 型別提示 (Type Hints) 完整度

### 現狀分析

| 檔案 | 型別提示完整度 | 備註 |
|------|---------------|------|
| `app/models.py` | ✅ 良好 | 使用 dataclass，型別完整 |
| `app/db.py` | ⚠️ 中等 | 缺少部分函數回傳型別 |
| `app/repositories.py` | ⚠️ 中等 | 大部分函數有型別，但 `dict` 缺少詳細註解 |
| `app/services/ingest.py` | ⚠️ 中等 | 部分內部函數缺少型別 |
| `app/services/diff.py` | ✅ 良好 | 型別完整 |
| `app/adapters/*.py` | ⚠️ 中等 | `Any` 使用過多，缺少具體型別 |

### 發現的問題

#### 1.1 `app/db.py` - 缺少型別提示

```python
# 現狀
def get_connection():
    # 缺少回傳型別

def _row_to_dict(row) -> dict:
    # dict 缺少鍵值型別
```

**建議改進：**

```python
from typing import Any
from collections.abc import Iterator

def get_connection() -> sqlite3.Connection | PostgresCompatConnection:
    ...

def _row_to_dict(row: sqlite3.Row | dict) -> dict[str, Any]:
    ...
```

#### 1.2 `app/repositories.py` - 字典型別不具體

```python
# 現狀
def list_etfs() -> list[dict]:
    def get_etf(ticker: str) -> Optional[dict]:
    def get_diffs(ticker: str, trade_date: str) -> list[dict]:
```

**建議改進：** 定義具體的 TypedDict

```python
from typing import TypedDict, NotRequired

class ETFDict(TypedDict):
    ticker: str
    name: str
    source_type: str
    source_url: str
    source_config: dict[str, Any]
    is_active: bool
    latest_trade_date: NotRequired[str | None]
    latest_fetched_at: NotRequired[str | None]
    last_run_status: NotRequired[str | None]
    last_run_finished_at: NotRequired[str | None]
    last_run_error: NotRequired[str | None]

class HoldingDiffDict(TypedDict):
    instrument_key: str
    instrument_name: str
    change_type: str
    quantity_delta: float
    weight_delta: float | None
    prev_quantity: float | None
    curr_quantity: float | None
    prev_weight: float | None
    curr_weight: float | None
    quantity_delta_pct: float | None
    quantity_delta_lots: float
    prev_quantity_lots: float | None
    curr_quantity_lots: float | None

def list_etfs() -> list[ETFDict]:
    def get_etf(ticker: str) -> ETFDict | None:
    def get_diffs(ticker: str, trade_date: str) -> list[HoldingDiffDict]:
```

#### 1.3 `app/adapters/base.py` - 抽象類別型別

```python
# 現狀
def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
```

**建議改進：** 允許回傳不同型別（如 `fhtrust_etf_html` 回傳 dict）

```python
from typing import Any

RawData = str | dict[str, Any]  # 定義聯合型別

class SourceAdapter(ABC):
    @abstractmethod
    def fetch(
        self, source_url: str, source_config: dict[str, Any]
    ) -> RawData:
        raise NotImplementedError
    
    @abstractmethod
    def parse(
        self, raw_data: RawData, source_config: dict[str, Any]
    ) -> tuple[str, list[Holding]]:
        raise NotImplementedError
```

---

## 2. 程式碼重複 - 適配器重複邏輯

### 現狀分析

多個適配器中存在大量重複的輔助函數：

| 重複函數 | 出現次數 | 檔案 |
|---------|---------|------|
| `_parse_float()` | 5 | nomura, unified, fhtrust, capital, tsit |
| `_assert_target_date()` | 3 | fhtrust, capital, tsit |
| `_parse_date()` | 3 | fhtrust, capital, tsit |
| User-Agent header | 5 | 所有適配器 |

### 發現的問題

#### 2.1 重複的 `_parse_float` 實作

**nomura_etfweb.py:**
```python
def _parse_float(self, value: str) -> Optional[float]:
    text = value.strip().replace(",", "").replace("%", "")
    if not text or text in {"-", "--", "N/A"}:
        return None
    return float(text)
```

**fhtrust_etf_html.py:** (完全相同)
```python
def _parse_float(self, value: str) -> Optional[float]:
    text = value.strip().replace(",", "").replace("%", "")
    if not text or text in {"-", "--", "N/A"}:
        return None
    return float(text)
```

**tsit_etf_detail.py:** (略有不同，有 try/except)
```python
def _parse_float(self, value: str) -> Optional[float]:
    text = value.strip().replace(",", "").replace("%", "")
    if not text or text in {"-", "--", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None
```

**建議改進：** 在 `base.py` 中提取為公用工具函數

```python
# app/adapters/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from app.models import Holding

def parse_float(value: Any) -> Optional[float]:
    """Parse a string value to float, handling common edge cases."""
    if value in (None, "", "-", "--", "N/A"):
        return None
    try:
        text = str(value).strip().replace(",", "").replace("%", "")
        if not text:
            return None
        return float(text)
    except (ValueError, TypeError):
        return None

def parse_date(value: str, formats: tuple[str, ...] | None = None) -> str:
    """Parse date string to ISO format."""
    from datetime import datetime
    
    if formats is None:
        formats = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y")
    
    value = value.strip()
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {value}")

class SourceAdapter(ABC):
    # 保持抽象方法
    ...
```

然後適配器直接使用：
```python
from app.adapters.base import parse_float, parse_date

class NomuraEtfWebAdapter(SourceAdapter):
    def _parse_float(self, value: str) -> Optional[float]:
        return parse_float(value)
    
    def _parse_date(self, value: str) -> str:
        return parse_date(value)
```

#### 2.2 重複的 User-Agent Header

所有適配器都重複定義相同的 User-Agent：

```python
headers={
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    )
}
```

**建議改進：** 定義常數

```python
# app/adapters/constants.py
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15
```

#### 2.3 重複的日期正規化邏輯

`ingest.py` 和多個適配器都有類似的天數回退邏輯：

```python
# ingest.py
def _normalize_trade_date(trade_date: str, trust_today: bool = False) -> str:
    if trust_today:
        return trade_date
    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    parsed = datetime.fromisoformat(trade_date).date()
    if parsed == today:
        return (parsed - timedelta(days=1)).isoformat()
    return trade_date
```

```python
# capital_portfolio.py
def _normalize_reported_date(self, reported_date: str, source_config: dict[str, Any]) -> str:
    if source_config.get("same_day_fallback_to_previous_day", True):
        today = datetime.now(ZoneInfo("Asia/Taipei")).date()
        parsed = datetime.fromisoformat(reported_date).date()
        if parsed == today:
            return (parsed - timedelta(days=1)).isoformat()
    return reported_date
```

**建議改進：** 統一在 `ingest.py` 處理，適配器只回傳原始日期。

---

## 3. Error Handling 是否足夠

### 現狀分析

| 檔案 | 錯誤處理 | 備註 |
|------|---------|------|
| `app/main.py` | ⚠️ 中等 | 只有 ingest 有 try/except |
| `app/services/ingest.py` | ✅ 良好 | 完整的錯誤記錄 |
| `app/adapters/*.py` | ⚠️ 中等 | 缺少 request 特定錯誤處理 |
| `app/repositories.py` | ❌ 不足 | 資料庫錯誤未處理 |

### 發現的問題

#### 3.1 適配器缺少 Request 特定錯誤處理

**現狀：**
```python
def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
    response = requests.get(source_url, timeout=15, headers={...})
    response.raise_for_status()
    return response.text
```

**建議改進：**
```python
from requests import RequestException, Timeout, HTTPError

class SourceFetchError(Exception):
    """Custom exception for source fetch failures."""
    pass

def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
    try:
        response = requests.get(source_url, timeout=15, headers={...})
        response.raise_for_status()
        return response.text
    except Timeout:
        raise SourceFetchError(f"Request timed out for {source_url}")
    except HTTPError as e:
        raise SourceFetchError(f"HTTP error {e.response.status_code} for {source_url}")
    except RequestException as e:
        raise SourceFetchError(f"Request failed for {source_url}: {e}")
```

#### 3.2 資料庫錯誤未處理

**現狀：** `repositories.py` 中所有資料庫操作都沒有錯誤處理。

**建議改進：**
```python
from app.db import get_connection, is_postgres

def list_etfs() -> list[ETFDict]:
    try:
        with get_connection() as connection:
            rows = connection.execute(...).fetchall()
        # process rows
    except sqlite3.Error as e:
        logger.error(f"Database error in list_etfs: {e}")
        raise  # 或回傳空列表，視需求而定
```

#### 3.3 缺少自定義異常類別

**建議新增：**
```python
# app/exceptions.py
class ETFTrackingError(Exception):
    """Base exception for ETF tracking errors."""
    pass

class SourceFetchError(ETFTrackingError):
    """Error fetching data from source."""
    pass

class SourceParseError(ETFTrackingError):
    """Error parsing source data."""
    pass

class ValidationError(ETFTrackingError):
    """Data validation error."""
    pass

class DatabaseError(ETFTrackingError):
    """Database operation error."""
    pass
```

---

## 4. 函數複雜度

### 現狀分析

| 函數 | 位置 | 圈複雜度 | 建議 |
|------|------|---------|------|
| `_build_card()` | main.py | 高 | 拆分 |
| `_run_scheduled_refresh_with_retry()` | main.py | 高 | 拆分 |
| `_extract_stock_rows()` | capital_portfolio.py | 高 | 拆分 |
| `_parse_assets_excel()` | fhtrust_etf_html.py | 高 | 拆分 |
| `build_diffs()` | diff.py | 中 | 可接受 |

### 發現的問題

#### 4.1 `_build_card()` 函數過大

**現狀：** 230+ 行，負責太多事情

**建議拆分：**
```python
def _build_card(etf_item: dict, today: str) -> dict:
    metadata = _get_latest_metadata(etf_item["ticker"])
    latest_run = get_latest_crawl_run(etf_item["ticker"])
    diffs = _get_diffs_for_card(etf_item["ticker"], metadata["trade_date"])
    grouped = _group_diffs_by_type(diffs)
    
    return {
        "etf": get_etf(etf_item["ticker"]),
        "latest_date": metadata["trade_date"],
        "latest_fetched_at": metadata["fetched_at"],
        "latest_fetched_at_display": _format_datetime(metadata["fetched_at"]),
        "is_stale": bool(metadata["trade_date"] and metadata["trade_date"] != today),
        "display_diffs": _top_weight_diffs(diffs, limit=10),
        "grouped_diffs": grouped,
        "summary": {key: len(value) for key, value in grouped.items()},
        "last_run_status": latest_run["status"] if latest_run else None,
        "last_run_finished_at": latest_run["finished_at"] if latest_run else None,
        "last_run_finished_at_display": _format_datetime(
            latest_run["finished_at"], include_date=False
        ) if latest_run else None,
        "last_run_error": latest_run["error_message"] if latest_run else None,
    }

def _get_latest_metadata(ticker: str) -> dict:
    metadata = get_latest_snapshot_metadata(ticker)
    if not metadata:
        return {"trade_date": None, "fetched_at": None}
    return metadata

def _get_diffs_for_card(ticker: str, trade_date: str | None) -> list[dict]:
    if not trade_date:
        return []
    return get_diffs(ticker, trade_date)

def _group_diffs_by_type(diffs: list[dict]) -> dict[str, list[dict]]:
    return {
        "enter_top10": [d for d in diffs if d["change_type"] == "enter_top10"],
        "increase": [d for d in diffs if d["change_type"] == "increase"],
        "decrease": [d for d in diffs if d["change_type"] == "decrease"],
        "exit_top10": [d for d in diffs if d["change_type"] == "exit_top10"],
    }
```

#### 4.2 `_extract_stock_rows()` 包含兩種解析邏輯

**建議拆分：**
```python
def _extract_stock_rows(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
    section = self._find_stock_section(soup)
    rows = self._try_extract_from_pct_table(section)
    if rows:
        return rows
    return self._fallback_to_standard_table(section)

def _find_stock_section(self, soup: BeautifulSoup) -> Tag:
    section = soup.select_one("#buyback-stocks-section")
    if not section:
        raise ValueError("Unable to locate stock holdings section")
    return section

def _try_extract_from_pct_table(self, section: Tag) -> list[dict[str, Any]]:
    # 原有邏輯
    ...

def _fallback_to_standard_table(self, section: Tag) -> list[dict[str, Any]]:
    # 原有邏輯
    ...
```

---

## 5. 命名規範

### 現狀分析

| 問題 | 位置 | 建議 |
|------|------|------|
| `_rows_to_holdings()` 與 `get_snapshot()` 命名不一致 | ingest.py | 統一為 snake_case |
| `trade_date` vs `tradeDate` | 部分 JSON | 統一為 snake_case |
| `source_type` vs `adapter_type` | 全域 | 建議統一為 `source_type` |

### 發現的問題

#### 5.1 函數命名風格不一致

```python
# ingest.py - 使用 _ 前綴表示私有
def _rows_to_holdings(rows: list[dict]) -> list[Holding]:
def _now_iso() -> str:
def _normalize_trade_date(trade_date: str, trust_today: bool = False) -> str:

# main.py - 混用
def _format_datetime(...) -> Optional[str]:  # 私有
def _diff_weight_value(diff: dict) -> float:  # 私有
def health() -> dict:  # 公開
def get_etfs() -> list[dict]:  # 公開
```

**建議：** 保持現有風格，但確保一致性。目前已經相當一致。

#### 5.2 變數命名可改進

```python
# repositories.py
seed_rows_pg = [...]  # 建議：postgres_seed_rows
seed_rows_sqlite = [...]  # 建議：sqlite_seed_rows
```

```python
# main.py
first_pass = refresh_active_etfs(...)  # 建議：initial_refresh_results
retry_candidates: list[str] = []  # 良好
```

---

## 6. 其他建議

### 6.1 新增日誌記錄

目前專案缺少系統化的日誌記錄：

```python
# app/logging_config.py
import logging
from pathlib import Path

def setup_logging(log_level: str = "INFO") -> None:
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "etf_tracking.log"),
            logging.StreamHandler(),
        ],
    )

# 在各模組中使用
import logging
logger = logging.getLogger(__name__)

def ingest_latest_snapshot(...) -> dict:
    logger.info(f"Starting ingest for {ticker}")
    try:
        # ...
    except Exception as exc:
        logger.error(f"Failed to ingest {ticker}: {exc}", exc_info=True)
        # ...
```

### 6.2 環境變數管理

建議使用 `pydantic-settings` 管理環境變數：

```python
# app/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str | None = None
    db_path: str | None = None
    vercel: bool = False
    disable_scheduler: bool = False
    schedule_retry_delay_seconds: int = 1800
    
    class Config:
        env_prefix = "ETF_TRACKING_"

settings = Settings()
```

### 6.3 測試覆蓋率

建議新增：
- 適配器 Mock 測試
- 資料庫錯誤處理測試
- 邊界條件測試

---

## 7. 重構優先級

| 優先級 | 項目 | 預期效益 |
|-------|------|---------|
| 🔴 高 | 提取重複的 `_parse_float` 等函數 | 減少維護成本 |
| 🔴 高 | 新增自定義異常類別 | 改善錯誤處理 |
| 🟡 中 | 完善型別提示 (TypedDict) | 改善 IDE 支援 |
| 🟡 中 | 拆分 `_build_card()` 函數 | 改善可讀性 |
| 🟡 中 | 新增日誌記錄 | 改善除錯能力 |
| 🟢 低 | 統一變數命名 | 改善一致性 |
| 🟢 低 | 環境變數管理 | 改善配置管理 |

---

## 8. 結論

本專案整體架構良好，主要改進方向為：

1. **消除重複程式碼**：將適配器的公用函數提取到 base 模組
2. **改善錯誤處理**：新增自定義異常類別，處理 Request 和 Database 錯誤
3. **完善型別提示**：使用 TypedDict 提供更精確的型別
4. **降低函數複雜度**：拆分大型函數
5. **新增日誌記錄**：改善生產環境的可觀測性

這些改進將提升程式碼的可維護性、可測試性和可讀性。
