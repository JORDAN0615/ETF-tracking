# ETF Tracking System - Feature Enhancements

## 概述

本文檔記錄了台灣主動式 ETF 追蹤系統的新功能增強，包括 API 增強、通知功能、資料匯出和环境變數設定。

---

## 1. API 增強

### 1.1 OpenAPI/Swagger 文件

FastAPI 內建 OpenAPI 文件，訪問以下端點查看：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

API 描述已更新為：
- 標題：Taiwan Active ETF Tracker
- 描述：追蹤台灣主動式 ETF 持股變動的 API 系統
- 版本：1.0.0

### 1.2 歷史資料查詢 API

#### GET /etfs/{ticker}/history

取得 ETF 的歷史持股資料，用於趨勢分析。

**參數**:
- `ticker` (path): ETF 代號
- `instrument_key` (query, optional): 篩選特定標的
- `limit` (query, default=50): 最大記錄數 (1-200)

**回應範例**:
```json
{
  "ticker": "00992A",
  "instrument_key": "2330",
  "history": [
    {
      "trade_date": "2024-01-15",
      "instrument_key": "2330",
      "instrument_name": "台積電",
      "instrument_type": "股票",
      "quantity": 50000,
      "quantity_lots": 50.0,
      "weight": 8.5
    }
  ]
}
```

#### GET /etfs/{ticker}/trend/{instrument_key}

取得特定標的的權重趨勢變化。

**回應範例**:
```json
{
  "ticker": "00992A",
  "instrument_key": "2330",
  "trend": [
    {"trade_date": "2024-01-01", "weight": 7.2, "quantity": 45000},
    {"trade_date": "2024-01-08", "weight": 7.8, "quantity": 48000},
    {"trade_date": "2024-01-15", "weight": 8.5, "quantity": 50000}
  ]
}
```

### 1.3 統計分析 API

#### GET /etfs/{ticker}/statistics

取得單一 ETF 的統計指標。

**回應範例**:
```json
{
  "ticker": "00992A",
  "latest_date": "2024-01-15",
  "concentration": {
    "top10_weight": 65.5,
    "top5_weight": 45.2,
    "top3_weight": 30.1,
    "herfindahl_index": 125.5,
    "effective_count": 79.68,
    "total_holdings": 100
  },
  "turnover": {
    "total_changes": 15,
    "new_entries": 3,
    "exits": 2,
    "increases": 8,
    "decreases": 2,
    "gross_turnover": 12.5,
    "net_turnover": 0.5
  },
  "holding_count": 100
}
```

**集中度指標說明**:
- `top10_weight`: 前十大持股權重總和
- `top5_weight`: 前五大持股權重總和
- `top3_weight`: 前三大持股權重總和
- `herfindahl_index`: 赫芬达尔指數 (HHI)，衡量集中度
- `effective_count`: 有效持股數 (1/HHI)

**轉換率指標說明**:
- `total_changes`: 總變動數量
- `new_entries`: 新進前十大
- `exits`: 退出前十大
- `increases`: 增持
- `decreases`: 減持
- `gross_turnover`: 總轉換率
- `net_turnover`: 淨轉換率

#### GET /etfs/statistics

取得所有 ETF 的統計指標。

---

## 2. 通知功能

### 2.1 Telegram 通知

當重大持股變動時自動發送 Telegram 通知。

**設定方式**:
在 `.env` 文件中設定：

```bash
# Telegram Bot Token (從 @BotFather 取得)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Telegram Chat ID (個人或群組 ID)
TELEGRAM_CHAT_ID=your_chat_id_here

# 通知閾值 (權重變化百分比)
ETF_NOTIFICATION_WEIGHT_THRESHOLD=5.0
```

**通知觸發條件**:
- 權重變化超過設定閾值 (預設 5%)
- 新進前十大持股
- 退出前十大持股

**通知範例**:
```
📈 ETF 持股重大變動通知

📌 ETF: 00992A (群益台灣科技創新主動式 ETF)
📅 交易日：2024-01-15

📊 標的：2330 (台積電)
🔄 變動類型：增持
權重變化：7.20% → 8.50% (+1.30%)
```

### 2.2 通知服務架構

```
app/services/notifications.py
├── TelegramNotifier
│   ├── send_message()
│   └── notify_major_change()
└── create_telegram_notifier()
```

---

## 3. 資料匯出

### 3.1 CSV 匯出

#### GET /etfs/{ticker}/holdings/export/csv?date={date}

匯出持股資料為 CSV 格式。

#### GET /etfs/{ticker}/diffs/export/csv?date={date}

匯出持股差異為 CSV 格式。

### 3.2 JSON 匯出

#### GET /etfs/{ticker}/holdings/export/json?date={date}

匯出持股資料為 JSON 格式。

#### GET /etfs/{ticker}/diffs/export/json?date={date}

匯出持股差異為 JSON 格式。

#### GET /etfs/export/json

匯出所有 ETF 摘要為 JSON 格式。

#### GET /etfs/{ticker}/statistics/export/json

匯出 ETF 統計指標為 JSON 格式。

### 3.3 Excel 匯出 (可選)

如需 Excel 匯出功能，請安裝 `openpyxl`:

```bash
pip install openpyxl
```

---

## 4. 環境變數設定

### 4.1 .env.example

已新增 `.env.example` 文件，包含所有可選環境變數：

```bash
# 資料庫設定
DATABASE_URL=postgresql://user:password@localhost:5432/etf_tracking
ETF_TRACKING_DB_PATH=/path/to/custom/etf_tracking.db

# Telegram 通知設定
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ETF_NOTIFICATION_WEIGHT_THRESHOLD=5.0

# 排程器設定
ETF_TRACKING_DISABLE_SCHEDULER=0
ETF_TRACKING_SCHEDULE_RETRY_DELAY_SECONDS=1800
```

### 4.2 使用方式

1. 複製範例文件：
   ```bash
   cp .env.example .env
   ```

2. 編輯 `.env` 文件，填入實際配置。

3. 重啟服務使設定生效。

---

## 5. 新增的 API 端點總覽

| 方法 | 端點 | 描述 |
|------|------|------|
| GET | /etfs/{ticker}/statistics | 取得 ETF 統計指標 |
| GET | /etfs/statistics | 取得所有 ETF 統計指標 |
| GET | /etfs/{ticker}/history | 取得歷史持股資料 |
| GET | /etfs/{ticker}/trend/{instrument_key} | 取得標的權重趨勢 |
| GET | /etfs/{ticker}/holdings/export/csv | 匯出持股 CSV |
| GET | /etfs/{ticker}/holdings/export/json | 匯出持股 JSON |
| GET | /etfs/{ticker}/diffs/export/csv | 匯出差異 CSV |
| GET | /etfs/{ticker}/diffs/export/json | 匯出差異 JSON |
| GET | /etfs/export/json | 匯出所有 ETF 摘要 |
| GET | /etfs/{ticker}/statistics/export/json | 匯出統計指標 JSON |

---

## 6. 新增的檔案

```
app/services/
├── export.py          # 資料匯出服務
├── notifications.py   # Telegram 通知服務
├── statistics.py      # 統計分析服務
└── __init__.py        # 更新服務匯出

.env.example           # 環境變數範例
```

---

## 7. 測試

### 7.1 API 測試

```bash
# 測試統計 API
curl http://localhost:8000/etfs/00992A/statistics

# 測試歷史資料 API
curl "http://localhost:8000/etfs/00992A/history?limit=10"

# 測試趨勢 API
curl http://localhost:8000/etfs/00992A/trend/2330

# 測試匯出 API
curl "http://localhost:8000/etfs/00992A/holdings/export/csv?date=2024-01-15" -o holdings.csv
```

### 7.2 通知測試

設定環境變數後，執行：

```bash
# 手動觸發抓取以測試通知
curl -X POST http://localhost:8000/etfs/00992A/fetch
```

---

## 8. 注意事項

1. **Telegram 通知**: 需要設定 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 才能啟用。

2. **Excel 匯出**: 需要安裝 `openpyxl` 套件。

3. **歷史資料**: 需要資料庫中已有歷史快照資料才能查詢。

4. **統計指標**: 轉換率指標需要前一期資料才能計算。

---

## 9. 未來擴展建議

1. 新增 WebSocket 即時通知
2. 支援更多匯出格式 (PDF, XML)
3. 新增郵件通知
4. 新增 Dashboard 圖表視覺化
5. 支援多 ETF 比較分析
