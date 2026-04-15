"""Parallel development utilities for dev team agents."""

from __future__ import annotations

import asyncio
import concurrent.futures
from pathlib import Path
from typing import Optional

from dev_agents.frontend.frontend_agent import FrontendAgent
from dev_agents.backend.backend_agent import BackendAgent
from dev_agents.qa.qa_agent import QAAgent


class ParallelDeveloper:
    """
    Enables parallel development across Frontend and Backend agents.
    
    Usage:
        developer = ParallelDeveloper()
        results = developer.develop_parallel(
            backend_task={"type": "create_endpoint", ...},
            frontend_task={"type": "enhance_template", ...}
        )
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize parallel developer with agents."""
        self.project_path = project_path
        self.frontend = FrontendAgent(project_path)
        self.backend = BackendAgent(project_path)
        self.qa = QAAgent(project_path)
    
    def develop_parallel(
        self,
        backend_task: dict,
        frontend_task: dict,
        run_qa: bool = True,
        max_workers: int = 2
    ) -> dict:
        """
        Develop frontend and backend in parallel.
        
        Args:
            backend_task: Backend development task
            frontend_task: Frontend development task
            run_qa: Whether to run QA after both complete
            max_workers: Maximum parallel workers
            
        Returns:
            Dict with results from all agents
        """
        print(f"\n🚀 Starting parallel development...")
        print(f"   Backend task: {backend_task.get('type', 'unknown')}")
        print(f"   Frontend task: {frontend_task.get('type', 'unknown')}")
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit both tasks
            backend_future = executor.submit(self.backend.execute_task, backend_task)
            frontend_future = executor.submit(self.frontend.execute_task, frontend_task)
            
            # Wait for both to complete
            concurrent.futures.wait(
                [backend_future, frontend_future],
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            # Get results
            backend_result = backend_future.result()
            frontend_result = frontend_future.result()
        
        print(f"\n✅ Backend completed: {backend_result.status.value}")
        print(f"✅ Frontend completed: {frontend_result.status.value}")
        
        # Optional: Run QA after both complete
        qa_result = None
        if run_qa:
            print(f"\n🧪 Running QA validation...")
            qa_task = {
                "type": "run_tests",
                "test_type": "all",
                "verbose": True
            }
            qa_result = self.qa.execute_task(qa_task)
            print(f"✅ QA completed: {qa_result.status.value}")
        
        return {
            "backend": backend_result.to_dict(),
            "frontend": frontend_result.to_dict(),
            "qa": qa_result.to_dict() if qa_result else None,
            "summary": {
                "backend_status": backend_result.status.value,
                "frontend_status": frontend_result.status.value,
                "qa_status": qa_result.status.value if qa_result else "skipped",
                "parallel": True
            }
        }
    
    def develop_sequential(
        self,
        backend_task: dict,
        frontend_task: dict,
        run_qa: bool = True
    ) -> dict:
        """
        Develop frontend and backend sequentially (for comparison).
        
        Args:
            backend_task: Backend development task
            frontend_task: Frontend development task
            run_qa: Whether to run QA after both complete
            
        Returns:
            Dict with results from all agents
        """
        print(f"\n📋 Starting sequential development...")
        
        # Backend first
        print(f"   Step 1: Backend task")
        backend_result = self.backend.execute_task(backend_task)
        print(f"   ✅ Backend completed: {backend_result.status.value}")
        
        # Frontend second
        print(f"   Step 2: Frontend task")
        frontend_result = self.frontend.execute_task(frontend_task)
        print(f"   ✅ Frontend completed: {frontend_result.status.value}")
        
        # QA
        qa_result = None
        if run_qa:
            print(f"   Step 3: QA validation")
            qa_task = {
                "type": "run_tests",
                "test_type": "all",
                "verbose": True
            }
            qa_result = self.qa.execute_task(qa_task)
            print(f"   ✅ QA completed: {qa_result.status.value}")
        
        return {
            "backend": backend_result.to_dict(),
            "frontend": frontend_result.to_dict(),
            "qa": qa_result.to_dict() if qa_result else None,
            "summary": {
                "backend_status": backend_result.status.value,
                "frontend_status": frontend_result.status.value,
                "qa_status": qa_result.status.value if qa_result else "skipped",
                "parallel": False
            }
        }


async def develop_async_parallel(
    backend_task: dict,
    frontend_task: dict,
    project_path: Path = None
) -> dict:
    """
    Async version of parallel development.
    
    Args:
        backend_task: Backend development task
        frontend_task: Frontend development task
        project_path: Path to project
        
    Returns:
        Dict with results from all agents
    """
    frontend = FrontendAgent(project_path)
    backend = BackendAgent(project_path)
    
    print(f"\n🚀 Starting async parallel development...")
    
    # Run both tasks concurrently
    backend_result = backend.execute_task(backend_task)
    frontend_result = frontend.execute_task(frontend_task)
    
    return {
        "backend": backend_result.to_dict(),
        "frontend": frontend_result.to_dict(),
        "parallel": True
    }


# Example usage
if __name__ == "__main__":
    import json
    
    developer = ParallelDeveloper()
    
    # Example: Develop ETF comparison feature in parallel
    print("="*60)
    print("PARALLEL DEVELOPMENT EXAMPLE")
    print("="*60)
    
    results = developer.develop_parallel(
        backend_task={
            "type": "create_endpoint",
            "method": "GET",
            "path": "/etfs/compare",
            "description": "Compare holdings across multiple ETFs",
            "request_schema": {
                "query": {
                    "tickers": {"type": "str"},
                    "date": {"type": "str", "default": "None"}
                }
            },
            "response_schema": {"type": "dict"},
            "implementation": {
                "func_name": "compare_etfs",
                "body": "return {'tickers': tickers, 'comparison': []}"
            }
        },
        frontend_task={
            "type": "add_chart",
            "template_name": "detail.html",
            "chart_type": "bar",
            "data_source": "/etfs/compare",
            "config": {
                "title": "ETF 持股比較",
                "label": "權重 (%)",
                "color": "#34a853"
            }
        },
        run_qa=False  # Skip QA for demo
    )
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(json.dumps(results["summary"], indent=2, ensure_ascii=False))
