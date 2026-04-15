# ETF Tracking System - Subagent Architecture

## 概述

本文件檔描述為 ETF Tracking System 設計的自主 Subagent 架構，使用 Hermes Agent 的 delegate_task 功能實現。

## 設計目標

1. **模組化**: 每個 Agent 負責單一職責
2. **可擴展**: 輕鬆新增投信來源或分析功能
3. **容錯性**: 個別 Agent 失敗不影響整體系統
4. **並行處理**: 多個 Agent 同時執行提高效率
5. **可監控**: 完整的日誌和狀態追蹤

---

## 架構圖

```
┌─────────────────────────────────────────────────────────┐
│              ETFManagerAgent (Orchestrator)             │
│  - 協調所有子 Agent                                      │
│  - 排程管理                                              │
│  - 錯誤處理與重試                                        │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
┌────────▼────────┐ ┌▼─────────┐ ┌▼─────────────────┐
│ Fetching Agents │ │Analysis  │ │Maintenance Agents│
│                 │ │ Agents   │ │                  │
│ • NomuraAgent   │ │• Stats   │ │ • HealthCheck    │
│ • CapitalAgent  │ │• Trend   │ │ • Backup         │
│ • FHTrustAgent  │ │• Alert   │ │ • Migration      │
│ • TSITAgent     │ │          │ │                  │
│ • UnifiedAgent  │ │          │ │                  │
└─────────────────┘ └──────────┘ └──────────────────┘
```

---

## Agent 詳細設計

### 1. ETFManagerAgent (主協調器)

**職責**:
- 觸發資料抓取流程
- 協調分析任務
- 管理錯誤和重試
- 生成綜合報告

**輸入**:
```python
{
    "action": "refresh_all" | "refresh_single" | "analyze" | "report",
    "ticker": "00992A",  # 可選
    "date": "2024-01-15",  # 可選
    "trust_today": True,  # 可選
}
```

**輸出**:
```python
{
    "status": "success" | "failed",
    "results": [...],
    "summary": {...},
    "errors": [...],
}
```

---

### 2. Data Fetching Agents

#### 2.1 NomuraAgent (野村投信)

**負責 ETF**: 00992A, 00981A

**職責**:
- 抓取野村官方 Fund/GetFundAssets API
- 解析 JSON 回應
- 驗證資料完整性
- 錯誤處理與重試

**工具**:
- `browser_navigate` - 訪問 API 端點
- `execute_code` - 資料解析和驗證
- `terminal` - 調用現有的 adapter 函數

**工作流程**:
```
1. 接收 ticker 和 target_date
2. 構建 API 請求
3. 發送請求並取得回應
4. 解析 JSON 資料
5. 驗證資料格式
6. 回傳標準化格式
```

**輸入**:
```python
{
    "ticker": "00992A",
    "target_date": "2024-01-15",  # 可選
}
```

**輸出**:
```python
{
    "trade_date": "2024-01-15",
    "holdings": [
        {
            "instrument_key": "2330",
            "instrument_name": "台積電",
            "instrument_type": "股票",
            "quantity": 50000,
            "weight": 8.5,
        },
    ],
    "status": "success",
    "raw_data_path": "/tmp/nomura_00992A_20240115.json",  # 可選
}
```

---

#### 2.2 CapitalAgent (群益投信)

**負責 ETF**: 00992A (備用來源)

**職責**:
- 抓取群益 portfolio 頁面
- 解析 HTML 表格
- 處理多種表格格式

**特殊處理**:
- 支援兩種表格格式 (% 欄位版和標準版)
- 自動偵測並切換解析策略

---

#### 2.3 FHTrustAgent (復華投信)

**負責 ETF**: 00987A

**職責**:
- 抓取 ETF 詳情頁
- 解析內嵌 Excel 資料
- 處理 base64 編碼的表格

---

#### 2.4 TSITAgent (台新投信)

**負責 ETF**: 00987A (備用)

**職責**:
- 抓取台新 ETF 詳情頁
- 解析官方持股表

---

#### 2.5 UnifiedAgent (統一投信)

**負責 ETF**: 其他統一投信產品

**職責**:
- 抓取 DataAsset 內嵌資料
- 解析 JSON 結構

---

### 3. Analysis Agents

#### 3.1 StatisticsAgent (統計分析)

**職責**:
- 計算集中度指標 (HHI, top10, top5, top3)
- 計算轉換率指標
- 生成統計報表

**輸入**:
```python
{
    "ticker": "00992A",
    "date_range": {
        "start": "2024-01-01",
        "end": "2024-01-15",
    },
}
```

**輸出**:
```python
{
    "concentration": {
        "top10_weight": 65.5,
        "top5_weight": 45.2,
        "top3_weight": 30.1,
        "herfindahl_index": 125.5,
        "effective_count": 79.68,
    },
    "turnover": {
        "gross_turnover": 12.5,
        "net_turnover": 0.5,
    },
}
```

---

#### 3.2 TrendAgent (趨勢分析)

**職責**:
- 追蹤特定標的的權重變化
- 識別長期趨勢
- 生成趨勢圖表資料

**輸入**:
```python
{
    "ticker": "00992A",
    "instrument_key": "2330",
    "period_days": 90,
}
```

**輸出**:
```python
{
    "trend": [
        {"date": "2024-01-01", "weight": 7.2, "quantity": 45000},
        {"date": "2024-01-08", "weight": 7.8, "quantity": 48000},
        {"date": "2024-01-15", "weight": 8.5, "quantity": 50000},
    ],
    "trend_direction": "increasing",
    "change_pct": 18.06,
}
```

---

#### 3.3 AlertAgent (異常偵測)

**職責**:
- 偵測重大持股變動
- 識別異常模式
- 觸發通知

**偵測規則**:
1. 單日權重變化 > 5%
2. 新進前十大持股
3. 退出前十大持股
4. 連續 N 日同向變動

**輸入**:
```python
{
    "ticker": "00992A",
    "current_date": "2024-01-15",
    "thresholds": {
        "weight_change": 5.0,
        "consecutive_days": 3,
    },
}
```

**輸出**:
```python
{
    "alerts": [
        {
            "type": "major_weight_change",
            "instrument": "2330",
            "message": "台積電權重從 7.2% 增加到 8.5% (+1.3%)",
            "severity": "medium",
        },
        {
            "type": "new_entry",
            "instrument": "2454",
            "message": "元大台灣 50 新進前十大",
            "severity": "high",
        },
    ],
}
```

---

### 4. Maintenance Agents

#### 4.1 HealthCheckAgent

**職責**:
- 檢查 API 可用性
- 驗證資料庫連線
- 監控系統資源

---

#### 4.2 BackupAgent

**職責**:
- 定期備份資料庫
- 壓縮歷史資料
- 管理儲存空間

---

#### 4.3 MigrationAgent

**職責**:
- SQLite → Postgres 遷移
- 資料格式升級
- 結構變更管理

---

## 實作方式

### 使用 Hermes delegate_task

每個 Agent 透過 `delegate_task` 工具啟動為獨立子程序：

```python
from hermes_tools import delegate_task

def run_nomura_agent(ticker: str, target_date: str = None) -> dict:
    """啟動 NomuraAgent 抓取野村 ETF 資料"""
    
    goal = f"Fetch ETF holdings data for {ticker} from Nomura source"
    
    context = f"""
    You are the NomuraAgent, responsible for fetching ETF data from Nomura Trust & Banking.
    
    Task: Fetch holdings for ETF {ticker}
    Target Date: {target_date or 'latest'}
    
    Steps:
    1. Use the existing app.adapters.nomura_etfweb adapter
    2. Fetch data from Fund/GetFundAssets API
    3. Parse the JSON response
    4. Validate data integrity
    5. Return standardized format
    
    Existing code location: ~/Desktop/etf-tracking-system/app/adapters/nomura_etfweb.py
    
    Output format:
    {{
        "trade_date": "YYYY-MM-DD",
        "holdings": [
            {{
                "instrument_key": "2330",
                "instrument_name": "台積電",
                "instrument_type": "股票",
                "quantity": 50000,
                "weight": 8.5,
            }},
        ],
        "status": "success",
    }}
    """
    
    result = delegate_task(
        goal=goal,
        context=context,
        toolsets=["terminal", "file", "execute_code"],
        max_iterations=20,
    )
    
    return result[0]  # delegate_task returns a list
```

---

## 並行執行範例

```python
import asyncio
from hermes_tools import delegate_task

async def refresh_all_etfs_parallel():
    """並行刷新所有 ETF"""
    
    tasks = [
        delegate_task(
            goal=f"Fetch {ticker} from Nomura",
            context=f"NomuraAgent context for {ticker}",
            toolsets=["terminal", "file"],
        )
        for ticker in ["00992A", "00981A"]
    ]
    
    # 並行執行 (最多 3 個同時)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "status": "completed",
        "results": results,
    }
```

---

## 錯誤處理策略

### 1. 個別 Agent 失敗
- 記錄錯誤日誌
- 不影響其他 Agent
- 可獨立重試

### 2. 重試機制
```python
max_retries = 3
backoff_seconds = 30

for attempt in range(max_retries):
    try:
        result = run_nomura_agent(ticker)
        if result["status"] == "success":
            break
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(backoff_seconds * (attempt + 1))
        else:
            log_error(f"Failed after {max_retries} attempts")
```

### 3. Fallback 來源
```python
def fetch_with_fallback(ticker: str) -> dict:
    """主來源失敗時使用備用來源"""
    
    # 嘗試主來源
    result = run_nomura_agent(ticker)
    if result["status"] == "success":
        return result
    
    # Fallback 到備用來源
    log_warning(f"Nomura failed, trying Capital for {ticker}")
    return run_capital_agent(ticker)
```

---

## 監控與日誌

### 日誌格式
```
{timestamp} [{level}] [{agent_name}] {message}
```

### 監控指標
- Agent 執行時間
- 成功/失敗率
- 資料完整性檢查
- API 回應時間

---

## 部署建議

### 1. 本機開發
```bash
# 啟動 Hermes Agent
hermes

# 在對話中觸發 Agent
/agent run --name nomura --ticker 00992A
```

### 2. 自動化排程
```python
# 使用 cronjob 工具
from hermes_tools import cronjob

cronjob(
    action="create",
    name="daily-etf-refresh",
    prompt="Run ETFManagerAgent to refresh all active ETFs",
    schedule="0 20 * * *",  # 每日 20:00
    skills=["etf-tracking"],
)
```

### 3. Docker 容器化
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY ~/Desktop/etf-tracking-system .

# 安裝依賴
pip install -r requirements.txt

# 啟動服務
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 未來擴展

1. **Machine Learning Agents**
   - 預測持股變動
   - 識別投資模式

2. **Report Generation Agents**
   - 自動生成 PDF 報告
   - 圖表視覺化

3. **Cross-ETF Analysis Agents**
   - 多 ETF 比較
   - 相關性分析

4. **News Integration Agents**
   - 抓取相關新聞
   - 情緒分析

---

## 參考文件

- [Hermes delegate_task 文檔](https://github.com/jordan-park/hermes-agent/blob/main/AGENTS.md#delegatetask)
- [ETF Tracking System README](README.md)
- [Performance Optimization Guide](PERFORMANCE_OPTIMIZATION.md)

---

## 版本歷史

- v1.0 (2024-01-15): 初始架構設計
- v1.1 (TBD): 加入 ML Agents
- v1.2 (TBD): 加入 Report Generation
