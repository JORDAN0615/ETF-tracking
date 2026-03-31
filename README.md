# Taiwan Active ETF Tracker Prototype

最小可驗證概念版本，目標是追蹤 1 檔台灣主動式 ETF 的公開持股資料，存成每日 snapshot，並比較前後日差異。
目前已將資料來源抽成 adapter，依投信官方來源分流抓取與解析。

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Deploy (Vercel)

- 已內建 `vercel.json` 與 `api/index.py`，可直接部署 FastAPI。
- 設定 `DATABASE_URL` 後會直接使用 Postgres（建議 Supabase）。
- 若未設定 `DATABASE_URL` 才會 fallback 到本地 SQLite（Vercel 為 `/tmp/etf_tracking.db`）。
- Vercel 上會自動關閉 app 內建排程器（避免 serverless 背景任務問題）。
- 建議在 Vercel 專案環境變數加上：`ETF_TRACKING_DISABLE_SCHEDULER=1`（雙重保險）。

## SQLite -> Supabase Migration

1. 先在 Supabase 建好四張表：`etfs`, `holdings_snapshots`, `holding_diffs`, `crawl_runs`。
2. 執行一次性 migration 腳本：

```bash
.venv/bin/python scripts/migrate_sqlite_to_supabase.py \
  --sqlite-path data/etf_tracking.db \
  --database-url "$DATABASE_URL"
```

腳本會依序搬 `etfs -> holdings_snapshots -> holding_diffs -> crawl_runs`，並輸出搬遷前後 row count 與抽樣核對結果。

## System Behavior

- 每日 `20:00`（台北時區）自動抓取所有啟用 ETF。
- 若首次排程抓取失敗，預設 `30` 分鐘後重試一次（可用 `ETF_TRACKING_SCHEDULE_RETRY_DELAY_SECONDS` 調整）。
- 抓取流程採安全覆寫：`fetch -> parse -> validate` 全部成功後才會 transaction 寫入 `snapshot + diff`。
- 失敗時只記錄 `crawl_runs`，不覆蓋舊 snapshot 與舊 diff。

## API Specification

### `GET /health`
- 用途：健康檢查。
- 回傳：`{"status":"ok"}`。

### `GET /etfs`
- 用途：列出系統追蹤 ETF 與每檔最新狀態。
- 回傳重點：
  - `ticker`, `name`, `source_type`, `is_active`
  - `latest_trade_date`（最新成功資料日期）
  - `latest_fetched_at`（最後成功抓取時間）
  - `last_run_status` / `last_run_finished_at` / `last_run_error`（最近一次抓取結果）

### `POST /etfs/{ticker}/fetch`
- 用途：API 方式觸發單檔抓取（建議正式手動觸發入口）。
- Query 參數：
  - `target_date`（選填，格式 `YYYY-MM-DD`，用於可查歷史的來源）
- 成功回傳重點：
  - `status=success`
  - `trade_date`, `fetched_at`, `snapshot_count`, `diff_count`, `previous_trade_date`
- 失敗行為：
  - HTTP `502`，`detail` 內含失敗原因（且 DB 不覆蓋舊資料）。
  - 若 ticker 不存在，HTTP `404`。

### `GET /etfs/{ticker}/holdings?date=YYYY-MM-DD`
- 用途：查詢指定 ETF 指定資料日的 snapshot 明細。
- 回傳重點：
  - 最外層：`ticker`, `trade_date`, `fetched_at`
  - `holdings[]`：`instrument_key`, `instrument_name`, `quantity`, `weight`, `quantity_lots`

### `GET /etfs/{ticker}/diffs?date=YYYY-MM-DD`
- 用途：查詢指定 ETF 指定資料日的持股變化結果。
- Diff 語意（前10限定）：
  - `enter_top10`：進榜
  - `increase`：加碼
  - `decrease`：減碼
  - `exit_top10`：出榜
- 回傳重點：
  - `diffs[]`：`change_type`, `quantity_delta`, `quantity_delta_lots`, `quantity_delta_pct`, `weight_delta`, `curr_weight` 等欄位。

### `POST /refresh`
- 用途：一次觸發全部啟用 ETF 抓取（主要給前台「立即更新全部 ETF」使用）。
- 回應：`303` redirect 到首頁 `/`。

### `POST /etfs/{ticker}/refresh`
- 用途：單檔刷新（HTML redirect 版，與 `POST /etfs/{ticker}/fetch` 功能相同）。
- 備註：目前 UI 已移除單檔更新按鈕，但路由保留可用。

### `GET /`
- 用途：首頁（HTML）。
- 顯示內容：所有 ETF 卡片、資料日期、最後成功抓取時間、最近一次抓取狀態、前10差異摘要。

### `GET /etfs/{ticker}`
- 用途：單檔日報頁（HTML）。
- 顯示內容：該檔 ETF 的前10差異統計與完整明細表。

## Source Adapter

- `nomura_etfweb`: 野村官方 `Fund/GetFundAssets` API
- `unified_ezmoney`: 統一投信 ETF 頁面內嵌 `DataAsset` 資料
- `fhtrust_etf_html`: 復華投信 ETF 詳情頁的官方持股表
- `tsit_etf_detail`: 台新投信 ETF 詳情頁的官方持股表
- `capital_portfolio`: 群益投信 ETF `portfolio` 頁的官方持股表

首頁會顯示 ETF 名稱、資料日期、最後成功抓取時間、最近一次抓取狀態，以及依公開持股差異推估出的進榜 / 加碼 / 減碼 / 出榜清單（僅前10大持股比較）。
