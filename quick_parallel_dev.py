"""
快速啟動並行開發 - 使用 Hermes delegate_task

不需要寫 Python 程式碼，直接讓 Hermes 啟動多個 subagent！
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def create_parallel_dev_tasks(
    feature_name: str,
    backend_requirements: dict,
    frontend_requirements: dict,
    project_path: Optional[Path] = None
) -> list[dict]:
    """
    創建並行開發任務，供 Hermes delegate_task 使用。
    
    Args:
        feature_name: 功能名稱
        backend_requirements: Backend 需求
        frontend_requirements: Frontend 需求
        project_path: 專案路徑
        
    Returns:
        任務列表，可直接用於 delegate_task(tasks=...)
    """
    project_path = project_path or Path.home() / "Desktop" / "etf-tracking-system"
    
    tasks = []
    
    # Backend 任務
    backend_context = f"""
    你是 Backend Development Agent，負責 ETF Tracking System 的後端開發。
    
    專案路徑：{project_path}
    功能名稱：{feature_name}
    
    需求:
    {json.dumps(backend_requirements, indent=2, ensure_ascii=False)}
    
    請:
    1. 在 app/main.py 創建新的 API endpoint
    2. 在 app/services/ 創建必要的服務函數
    3. 更新資料庫查詢 (如需)
    4. 測試 API 是否正常工作
    
    完成後回報結果。
    """
    
    tasks.append({
        "goal": f"Backend: 開發 {feature_name} 的 API",
        "context": backend_context,
        "toolsets": ["terminal", "file", "execute_code"]
    })
    
    # Frontend 任務
    frontend_context = f"""
    你是 Frontend Development Agent，負責 ETF Tracking System 的前端開發。
    
    專案路徑：{project_path}
    功能名稱：{feature_name}
    
    需求:
    {json.dumps(frontend_requirements, indent=2, ensure_ascii=False)}
    
    請:
    1. 修改 templates/ 中的 HTML 模板
    2. 添加必要的 JavaScript/CSS
    3. 整合圖表庫 (Chart.js 等)
    4. 測試 UI 是否正常顯示
    
    完成後回報結果。
    """
    
    tasks.append({
        "goal": f"Frontend: 開發 {feature_name} 的 UI",
        "context": frontend_context,
        "toolsets": ["file", "browser"]
    })
    
    return tasks


# 使用範例
if __name__ == "__main__":
    tasks = create_parallel_dev_tasks(
        feature_name="ETF 持股比較",
        backend_requirements={
            "endpoint": "/etfs/compare",
            "method": "GET",
            "params": ["tickers", "date"],
            "description": "比較多個 ETF 的持股"
        },
        frontend_requirements={
            "template": "index.html",
            "chart_type": "bar",
            "features": ["ETF 選擇器", "比較圖表"]
        }
    )
    
    print("✅ 創建了以下任務:")
    for i, task in enumerate(tasks, 1):
        print(f"\n{i}. {task['goal']}")
        print(f"   工具集：{task['toolsets']}")
    
    print("\n" + "="*60)
    print("使用方式:")
    print("="*60)
    print("""
# 在 Hermes 對話中，直接執行:
delegate_task(tasks=[...])  # 將上面的 tasks 傳入

# Hermes 會自動並行執行兩個 subagent！
    """)
