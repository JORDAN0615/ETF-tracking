# ETF Tracking System - Development Team Agents

## 概述

本文件描述為 ETF Tracking System 設計的**開發團隊 Agent 架構**，包含三個專職 Agent：

1. **Frontend Development Agent** - UI/UX 開發
2. **Backend Development Agent** - API 和服務開發  
3. **QA Agent** - 測試和品質保證

這些 Agent 協同工作，形成完整的開發流程。

---

## 架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                   Project Manager (You)                      │
│              分配任務給各專職 Agent                           │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
┌────────▼────────┐ ┌▼─────────┐ ┌▼─────────────────┐
│  Frontend Agent │ │Backend   │ │    QA Agent      │
│                 │ │ Agent    │ │                  │
│ • HTML/Templates│ │• API     │ │ • Unit Tests     │
│ • Charts        │ │• Services│ │ • Integration    │
│ • UX Improvements││• DB      │ │ • Performance    │
│ • Responsive    │ │• Security│ │ • Bug Tracking   │
└─────────────────┘ └──────────┘ └──────────────────┘
         │           │           │
         └───────────┼───────────┘
                     │
              ┌──────▼───────┐
              │   Git Repo    │
              │  (Collaboration)│
              └───────────────┘
```

---

## 1. Frontend Development Agent

### 職責範圍

**HTML Templates**
- 修改 `templates/index.html` (首頁)
- 修改 `templates/detail.html` (單檔詳情頁)
- 新增響應式設計
- 改善使用者體驗

**圖表視覺化**
- 使用 Chart.js / D3.js 繪製趨勢圖
- 持股分佈圓餅圖
- 權重變化折線圖
- 比較圖表

**功能增強**
- 即時更新 (WebSocket / Polling)
- 搜尋和篩選功能
- 資料匯出 UI
- 行動裝置優化

### 工作流程

```
1. 接收需求 (例如：「新增持股趨勢圖表」)
2. 分析現有 template 結構
3. 選擇合適的圖表庫
4. 實作 HTML/CSS/JavaScript
5. 測試相容性
6. 提交變更並等待 QA 驗證
```

### 工具集

- `file` - 讀取/修改 template 文件
- `execute_code` - 測試 JavaScript 邏輯
- `browser` - 預覽 UI 變更
- `terminal` - 啟動本地伺服器測試

### 實作範例

```python
# dev_agents/frontend/frontend_agent.py

class FrontendAgent(BaseDevAgent):
    """Frontend Development Agent for ETF Tracking System."""
    
    @property
    def description(self) -> str:
        return "Develops and improves UI/UX for ETF tracking system"
    
    def enhance_template(self, template_name: str, feature: str) -> AgentResult:
        """
        Enhance an HTML template with new feature.
        
        Args:
            template_name: Template file name (e.g., "index.html")
            feature: Feature to add (e.g., "add holdings chart")
            
        Returns:
            AgentResult with implementation details
        ```
```

### 常見任務

| 任務 | 描述 | 預估時間 |
|------|------|---------|
| 新增趨勢圖表 | 在詳情頁添加持股權重趨勢圖 | 30-60 分鐘 |
| 改善首頁佈局 | 重新設計 ETF 卡片佈局 | 20-40 分鐘 |
| 行動裝置優化 | 確保手機/平板相容性 | 40-80 分鐘 |
| 新增搜尋功能 | 在持股表中添加搜尋欄位 | 15-30 分鐘 |

---

## 2. Backend Development Agent

### 職責範圍

**API 開發**
- 新增 RESTful endpoints
- 優化現有 API
- 實作 GraphQL (可選)
- API 文件維護

**服務層**
- 新增業務邏輯
- 優化資料處理
- 實作快取機制
- 背景任務處理

**資料庫**
- Schema 變更
- 查詢優化
- 索引管理
- 資料遷移

**安全性**
- 輸入驗證
- 認證/授權
- SQL 注入防護
- CORS 設定

### 工作流程

```
1. 接收需求 (例如：「新增多 ETF 比較 API」)
2. 設計 API 規格 (端點、參數、回應)
3. 實作路由和控制器
4. 實作服務層邏輯
5. 更新資料庫 (如需)
6. 撰寫 API 文件
7. 提交變更並等待 QA 測試
```

### 工具集

- `file` - 修改 Python 源碼
- `execute_code` - 測試邏輯
- `terminal` - 執行測試、啟動伺服器
- `browser` - 測試 API (Swagger UI)

### 實作範例

```python
# dev_agents/backend/backend_agent.py

class BackendAgent(BaseDevAgent):
    """Backend Development Agent for ETF Tracking System."""
    
    @property
    def description(self) -> str:
        return "Develops and maintains backend services and APIs"
    
    def create_api_endpoint(
        self,
        method: str,
        path: str,
        description: str,
        request_schema: dict,
        response_schema: dict
    ) -> AgentResult:
        """
        Create a new API endpoint.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Endpoint path (e.g., "/etfs/{ticker}/compare")
            description: Endpoint description
            request_schema: Request schema definition
            response_schema: Response schema definition
            
        Returns:
            AgentResult with implementation details
        ```
```

### 常見任務

| 任務 | 描述 | 預估時間 |
|------|------|---------|
| 新增比較 API | 支援多 ETF 持股比較 | 45-90 分鐘 |
| 優化查詢 | 改善慢查詢效能 | 30-60 分鐘 |
| 新增 WebSocket | 即時通知支援 | 60-120 分鐘 |
| 實作快取 | Redis 快取層 | 40-80 分鐘 |

---

## 3. QA Agent

### 職責範圍

**單元測試**
- 撰寫新功能的單元測試
- 維護現有測試套件
- 提高測試覆蓋率
- Mock 外部依賴

**整合測試**
- API 端點測試
- 資料庫整合測試
- 跨服務測試
- 端到端測試

**效能測試**
- 載入測試
- 壓力測試
- 記憶體使用分析
- 回應時間監控

**Bug 追蹤**
- 重現問題
- 診斷根本原因
- 驗證修復
- 回歸測試

### 工作流程

```
1. 接收測試需求 (例如：「測試新增的比較 API」)
2. 分析功能規格
3. 撰寫測試案例
4. 執行測試套件
5. 生成測試報告
6. 追蹤並驗證 Bug 修復
```

### 工具集

- `terminal` - 執行 pytest
- `file` - 撰寫測試腳本
- `execute_code` - 分析測試結果
- `browser` - 手動測試 UI

### 實作範例

```python
# dev_agents/qa/qa_agent.py

class QAAgent(BaseDevAgent):
    """QA Agent for ETF Tracking System."""
    
    @property
    def description(self) -> str:
        return "Ensures code quality through testing and validation"
    
    def run_test_suite(self, test_type: str = "all") -> AgentResult:
        """
        Run test suite and generate report.
        
        Args:
            test_type: Type of tests to run
                - "unit": Unit tests only
                - "integration": Integration tests only
                - "all": All tests (default)
                
        Returns:
            AgentResult with test results and coverage report
        ```
    
    def validate_feature(self, feature_name: str) -> AgentResult:
        """
        Validate a specific feature.
        
        Args:
            feature_name: Name of feature to validate
            
        Returns:
            AgentResult with validation outcome
        ```
```

### 測試覆蓋率目標

| 模組 | 目標覆蓋率 | 目前狀態 |
|------|-----------|---------|
| `app/adapters/` | 90% | ⏳ 待測量 |
| `app/services/` | 85% | ⏳ 待測量 |
| `app/repositories.py` | 80% | ⏳ 待測量 |
| `app/main.py` | 75% | ⏳ 待測量 |

### 常見任務

| 任務 | 描述 | 預估時間 |
|------|------|---------|
| 新增單元測試 | 為新功能撰寫測試 | 20-40 分鐘 |
| 效能測試 | 測試 API 回應時間 | 30-60 分鐘 |
| Bug 驗證 | 驗證修復是否有效 | 15-30 分鐘 |
| 回歸測試 | 確保沒有破壞現有功能 | 40-80 分鐘 |

---

## Agent 協同工作流程

### 完整開發流程範例

**需求**: 「新增多 ETF 持股比較功能」

#### Phase 1: 需求分析 (所有 Agent)

```
1. Backend Agent: 分析 API 需求
2. Frontend Agent: 分析 UI 需求
3. QA Agent: 規劃測試策略
```

#### Phase 2: 實作 (Backend + Frontend)

```
Backend Agent:
  1. 設計比較 API: GET /etfs/compare?tickers=00992A,00981A&date=2024-01-15
  2. 實作服務層邏輯
  3. 更新資料庫查詢
  
Frontend Agent:
  1. 設計比較頁面 UI
  2. 實作 ETF 選擇器
  3. 繪製比較圖表
```

#### Phase 3: 測試 (QA Agent)

```
QA Agent:
  1. 撰寫 API 單元測試
  2. 執行整合測試
  3. 驗證 UI 功能
  4. 生成測試報告
```

#### Phase 4: 部署 (所有 Agent)

```
1. QA Agent: 最終回歸測試
2. Backend Agent: 更新 API 文件
3. Frontend Agent: 確認生產環境顯示
```

---

## 溝通機制

### 1. 透過 Git

```bash
# Backend Agent 創建 feature branch
git checkout -b feature/etf-comparison-api

# Frontend Agent 創建 feature branch
git checkout -b feature/etf-comparison-ui

# QA Agent 創建 test branch
git checkout -b tests/etf-comparison
```

### 2. 透過共享狀態

```python
# dev_agents/shared_state.py

class DevState:
    """Shared state between agents."""
    
    def __init__(self):
        self.current_feature = None
        self.backend_ready = False
        self.frontend_ready = False
        self.qa_passed = False
    
    def mark_backend_ready(self, feature: str):
        self.current_feature = feature
        self.backend_ready = True
        print(f"✅ Backend ready for: {feature}")
    
    def mark_frontend_ready(self, feature: str):
        self.current_feature = feature
        self.frontend_ready = True
        print(f"✅ Frontend ready for: {feature}")
    
    def mark_qa_passed(self, feature: str):
        self.qa_passed = True
        print(f"✅ QA passed for: {feature}")
    
    def is_feature_complete(self, feature: str) -> bool:
        return (
            self.current_feature == feature and
            self.backend_ready and
            self.frontend_ready and
            self.qa_passed
        )
```

### 3. 透過事件驅動

```python
# 事件類型
EVENT_BACKEND_READY = "backend_ready"
EVENT_FRONTEND_READY = "frontend_ready"
EVENT_QA_PASSED = "qa_passed"
EVENT_DEPLOYMENT_READY = "deployment_ready"

# 事件監聽
class EventDispatcher:
    def __init__(self):
        self.listeners = {}
    
    def on(self, event_type: str, callback):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
    
    def emit(self, event_type: str, data: dict):
        for callback in self.listeners.get(event_type, []):
            callback(data)
```

---

## 實作檔案結構

```
dev_agents/
├── __init__.py              # 匯出所有 Agent
├── base.py                  # 基礎 Agent 類別
├── orchestrator.py          # 協調三個 Agent
├── shared_state.py          # 共享狀態管理
├── events.py                # 事件系統
│
├── frontend/
│   ├── __init__.py
│   ├── frontend_agent.py    # Frontend Agent 實作
│   ├── chart_templates/     # 圖表模板
│   └── style_guides/        # 樣式指南
│
├── backend/
│   ├── __init__.py
│   ├── backend_agent.py     # Backend Agent 實作
│   ├── api_templates/       # API 模板
│   └── db_migrations/       # 資料庫遷移
│
└── qa/
    ├── __init__.py
    ├── qa_agent.py          # QA Agent 實作
    ├── test_templates/      # 測試模板
    └── performance/         # 效能測試腳本
```

---

## 使用方式

### 1. 單一 Agent 模式

```python
from dev_agents import FrontendAgent, BackendAgent, QAAgent

# 啟動 Frontend Agent
frontend = FrontendAgent()
result = frontend.enhance_template(
    template_name="detail.html",
    feature="add holdings trend chart"
)

# 啟動 Backend Agent
backend = BackendAgent()
result = backend.create_api_endpoint(
    method="GET",
    path="/etfs/compare",
    description="Compare holdings across multiple ETFs"
)

# 啟動 QA Agent
qa = QAAgent()
result = qa.run_test_suite(test_type="all")
```

### 2. 協調模式 (Orchestrator)

```python
from dev_agents import DevOrchestrator

# 創建協調器
orchestrator = DevOrchestrator()

# 分配完整功能開發
result = orchestrator.develop_feature(
    feature_name="etf_comparison",
    description="Multi-ETF holdings comparison feature",
    requirements={
        "backend": {
            "api_endpoint": "/etfs/compare",
            "supports": ["holdings", "diffs", "statistics"]
        },
        "frontend": {
            "page": "/compare",
            "charts": ["bar", "line"],
            "interactive": True
        },
        "qa": {
            "coverage_target": 85,
            "performance_tests": True
        }
    }
)

# 等待所有 Agent 完成
print(f"Feature complete: {result.success}")
print(f"Test coverage: {result.test_coverage}%")
```

### 3. 透過 Hermes delegate_task

```python
from hermes_tools import delegate_task

# 啟動 Backend Agent 作為獨立子程序
result = delegate_task(
    goal="Create ETF comparison API endpoint",
    context="""
    You are the Backend Development Agent for ETF Tracking System.
    
    Task: Implement GET /etfs/compare endpoint
    
    Requirements:
    - Accept multiple tickers as query parameter
    - Return holdings comparison for specified date
    - Include diff analysis
    - Support pagination
    
    Code location: ~/Desktop/etf-tracking-system/app/main.py
    """,
    toolsets=["terminal", "file", "execute_code"],
    max_iterations=30
)
```

---

## 最佳實踐

### 1. 版本控制

- 每個 Agent 在獨立 branch 工作
- 使用 descriptive commit messages
- PR 必須通過 QA Agent 測試才能合併

### 2. 溝通

- Backend Agent 完成 API 後通知 Frontend Agent
- Frontend Agent 完成 UI 後通知 QA Agent
- QA Agent 發現 Bug 時創建 issue 並指派給對應 Agent

### 3. 測試

- 每個新功能必須有對應測試
- 測試覆蓋率不得低于 80%
- 效能測試必須在部署前通過

### 4. 文件

- API 變更必須更新 Swagger 文件
- UI 變更必須更新使用者指南
- 資料庫變更必須記錄 migration 文件

---

## 未來擴展

1. **DevOps Agent** - 自動部署和監控
2. **Security Agent** - 安全掃描和漏洞修復
3. **Documentation Agent** - 自動生成文件
4. **Performance Agent** - 持續效能優化

---

## 版本歷史

- v1.0 (2024-01-15): 初始開發團隊 Agent 架構
- v1.1 (TBD): 加入 DevOps Agent
- v1.2 (TBD): 加入 Security Agent
