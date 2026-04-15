# 並行開發 - 快速指南

## 🚀 最簡單的方式 (推薦！)

**不需要寫任何 Python 程式碼！** 直接使用 Hermes 的 `delegate_task`：

```python
# 在 Hermes 對話中直接執行:
delegate_task(
    tasks=[
        {
            "goal": "創建 ETF 比較 API endpoint",
            "context": """
            你是 Backend Agent，負責開發 ETF Tracking System。
            
            任務: 在 app/main.py 創建 GET /etfs/compare 端點
            參數：tickers (str), date (str, optional)
            功能：比較多個 ETF 的持股
            
            專案路徑：~/Desktop/etf-tracking-system
            """,
            "toolsets": ["terminal", "file", "execute_code"]
        },
        {
            "goal": "添加 ETF 比較圖表 UI",
            "context": """
            你是 Frontend Agent，負責開發 ETF Tracking System。
            
            任務：在 templates/index.html 添加比較圖表
            使用：Chart.js 棒圖
            資料來源：/etfs/compare API
            
            專案路徑：~/Desktop/etf-tracking-system
            """,
            "toolsets": ["file", "browser"]
        }
    ]
)
```

**Hermes 會自動並行執行這兩個 subagent！** ⚡

---

## 為什麼這樣更好？

### ❌ 舊方式 (我之前的做法)
```python
# 需要寫很多程式碼
from dev_agents import ParallelDeveloper

developer = ParallelDeveloper()

# 定義複雜的任務結構
backend_task = {
    "type": "create_endpoint",
    "method": "GET",
    "path": "/etfs/compare",
    "request_schema": {...},
    "response_schema": {...},
    "implementation": {...}
}

frontend_task = {
    "type": "add_chart",
    "template_name": "index.html",
    "chart_type": "bar",
    "data_source": "/etfs/compare",
    "config": {...}
}

# 調用並行方法
results = developer.develop_parallel(
    backend_task=backend_task,
    frontend_task=frontend_task
)
```

**問題**:
- 需要寫 30+ 行程式碼
- 需要定義複雜的任務結構
- 需要理解 ParallelDeveloper API
- 需要等待 Python 執行完

### ✅ 新方式 (直接使用 delegate_task)
```python
# 只需要幾行！
delegate_task(
    tasks=[
        {"goal": "創建 API", "context": "...", "toolsets": [...]},
        {"goal": "添加 UI", "context": "...", "toolsets": [...]}
    ]
)
```

**優點**:
- ✅ 只需要 5-10 行
- ✅ 直接用自然語言描述
- ✅ Hermes 自動處理並行
- ✅ 即時看到兩個 subagent 工作

---

## 實際案例

### 案例 1: 開發「持股趨勢圖」功能

```python
delegate_task(
    tasks=[
        {
            "goal": "創建持股趨勢 API",
            "context": """
            Backend Agent 任務:
            
            1. 在 app/main.py 添加: GET /etfs/{ticker}/trend/{instrument_key}
            2. 在 app/services/statistics.py 添加 get_weight_trend() 函數
            3. 查詢 holdings_snapshots 表，按日期排序
            4. 回傳：[{"date": "...", "weight": ..., "quantity": ...}]
            
            專案：~/Desktop/etf-tracking-system
            """,
            "toolsets": ["terminal", "file", "execute_code"]
        },
        {
            "goal": "添加趨勢圖表 UI",
            "context": """
            Frontend Agent 任務:
            
            1. 在 templates/detail.html 添加 Chart.js 折線圖
            2. 圖表顯示持股權重隨時間變化
            3. 添加日期選擇器
            4. 從 /etfs/{ticker}/trend/{instrument_key} 取得資料
            
            專案：~/Desktop/etf-tracking-system
            """,
            "toolsets": ["file", "browser"]
        }
    ]
)
```

**結果**: 兩個 subagent 同時開始工作，互不干擾！

---

### 案例 2: 開發「多 ETF 統計比較」功能

```python
delegate_task(
    tasks=[
        {
            "goal": "Backend: 創建統計比較 API",
            "context": "創建 GET /etfs/statistics/compare，支援比較多個 ETF 的集中度、轉換率等指標",
            "toolsets": ["terminal", "file"]
        },
        {
            "goal": "Frontend: 創建統計比較頁面",
            "context": "在 templates/ 新增 compare_stats.html，使用表格和儀表板顯示統計數據",
            "toolsets": ["file", "browser"]
        },
        {
            "goal": "QA: 測試新功能",
            "context": "為統計比較功能撰寫單元測試和整合測試",
            "toolsets": ["terminal", "file"]
        }
    ]
)
```

**結果**: 三個 subagent 同時工作！(Hermes 支援最多 3 個並行)

---

## 為什麼 Hermes 可以自動並行？

`delegate_task` 的 **batch 模式** 會：

1. **同時啟動** 所有 subagent (最多 3 個)
2. **獨立執行** 每個任務 (不同的 terminal/session)
3. **自動等待** 所有任務完成
4. **匯總結果** 回傳給你

```python
delegate_task(
    tasks=[task1, task2, task3]  # ← 這就會並行執行！
)
```

**不需要** 手動管理線程、不需要 `asyncio`、不需要 `ThreadPoolExecutor`！

---

## 對比總結

| 方式 | 程式碼量 | 需要理解 | 並行控制 | 推薦度 |
|------|---------|---------|---------|--------|
| **delegate_task batch** | 5-10 行 | 低 | 自動 | ⭐⭐⭐⭐⭐ |
| **ParallelDeveloper** | 30+ 行 | 中 | 手動 | ⭐⭐⭐ |
| **手動 threading** | 20+ 行 | 高 | 手動 | ⭐⭐ |

---

## 最佳實踐

### 1. 任務要獨立

```python
# ✅ 好：兩個任務互不干擾
tasks = [
    {"goal": "創建 API", "context": "..."},
    {"goal": "創建 UI", "context": "..."}
]

# ❌ 不好：UI 依賴 API 完成
tasks = [
    {"goal": "創建 API", "context": "..."},
    {"goal": "使用 API 創建 UI", "context": "需要等 API 完成..."}  # 會阻塞！
]
```

### 2. 使用 Mock 資料

如果前端需要後端資料，先用 mock：

```python
{
    "goal": "創建 UI",
    "context": """
    先用 mock 資料開發 UI:
    mock_data = [
        {"ticker": "00992A", "weight": 15.2},
        {"ticker": "00981A", "weight": 12.8}
    ]
    
    等 API 完成後再替換成真實 API 呼叫。
    """
}
```

### 3. 明確指定工具集

```python
{
    "goal": "Backend 任務",
    "toolsets": ["terminal", "file", "execute_code"]  # 後端需要的工具
}

{
    "goal": "Frontend 任務", 
    "toolsets": ["file", "browser"]  # 前端需要的工具
}
```

### 4. 提供完整上下文

```python
{
    "goal": "...",
    "context": """
    專案路徑：~/Desktop/etf-tracking-system
    相關檔案：app/main.py, templates/index.html
    現有功能：...
    需求細節：...
    """
}
```

---

## 常見問題

### Q: 兩個 subagent 會互相干擾嗎？

**A**: 不會！每個 subagent 有獨立的:
- Terminal session
- File system view
- Execution context

### Q: 如果一個失敗了怎麼辦？

**A**: 另一個繼續執行！你可以從結果中看到哪個失敗了，然後單獨重試。

### Q: 可以超過 3 個並行嗎？

**A**: 目前 Hermes 限制最多 3 個。如果需要更多，可以分批執行。

### Q: 如何知道哪個先完成？

**A**: delegate_task 會回傳所有結果，你可以檢查每個任務的完成狀態。

---

## 快速開始範本

```python
delegate_task(
    tasks=[
        {
            "goal": "Backend: [你的功能名稱]",
            "context": """
            你是 Backend Agent。
            
            專案：~/Desktop/etf-tracking-system
            
            任務:
            1. [具體任務 1]
            2. [具體任務 2]
            3. [具體任務 3]
            
            相關檔案:
            - app/main.py
            - app/services/
            """,
            "toolsets": ["terminal", "file", "execute_code"]
        },
        {
            "goal": "Frontend: [你的功能名稱]",
            "context": """
            你是 Frontend Agent。
            
            專案：~/Desktop/etf-tracking-system
            
            任務:
            1. [具體任務 1]
            2. [具體任務 2]
            
            相關檔案:
            - templates/
            - static/
            """,
            "toolsets": ["file", "browser"]
        }
    ]
)
```

---

## 總結

✅ **使用 `delegate_task(tasks=[...])`** - 最簡單！  
✅ **Hermes 自動處理並行** - 不用寫程式碼！  
✅ **最多 3 個 subagent 同時工作** - 效率最高！  
✅ **自然語言描述任務** - 最容易理解！  

**忘記 ParallelDeveloper 吧，直接用 delegate_task！** 🎉
