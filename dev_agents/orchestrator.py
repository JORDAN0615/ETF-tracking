"""Orchestrator for coordinating development team agents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from dev_agents.base import DevTaskResult, DevTaskStatus
from dev_agents.frontend.frontend_agent import FrontendAgent
from dev_agents.backend.backend_agent import BackendAgent
from dev_agents.qa.qa_agent import QAAgent


class DevOrchestrator:
    """
    Orchestrates Frontend, Backend, and QA agents for coordinated development.
    
    Usage:
        orchestrator = DevOrchestrator()
        result = orchestrator.develop_feature("etf-comparison", {...})
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize orchestrator with all agents."""
        self.project_path = project_path
        self.frontend = FrontendAgent(project_path)
        self.backend = BackendAgent(project_path)
        self.qa = QAAgent(project_path)
        
        self.logger = logging.getLogger("DevOrchestrator")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [Orchestrator] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(handler)
    
    def develop_feature(self, feature_name: str, requirements: dict) -> dict:
        """
        Orchestrate full feature development across all agents.
        
        Args:
            feature_name: Name of feature to develop
            requirements: Requirements for each agent
            
        Returns:
            Dict with results from all agents
        """
        self.logger.info(f"Starting feature development: {feature_name}")
        
        results = {}
        
        # Phase 1: Backend development
        self.logger.info("Phase 1: Backend development")
        if "backend" in requirements:
            backend_task = self._create_backend_task(requirements["backend"])
            results["backend"] = self.backend.execute_task(backend_task).to_dict()
            self.logger.info(f"Backend result: {results['backend']['status']}")
        
        # Phase 2: Frontend development
        self.logger.info("Phase 2: Frontend development")
        if "frontend" in requirements:
            frontend_task = self._create_frontend_task(requirements["frontend"])
            results["frontend"] = self.frontend.execute_task(frontend_task).to_dict()
            self.logger.info(f"Frontend result: {results['frontend']['status']}")
        
        # Phase 3: QA testing
        self.logger.info("Phase 3: QA testing")
        if "qa" in requirements:
            qa_task = self._create_qa_task(requirements["qa"], feature_name)
            results["qa"] = self.qa.execute_task(qa_task).to_dict()
            self.logger.info(f"QA result: {results['qa']['status']}")
        
        # Summary
        success = all(
            results.get(agent, {}).get("status") == "completed"
            for agent in ["backend", "frontend", "qa"]
        )
        
        self.logger.info(f"Feature development {'completed' if success else 'failed'}: {feature_name}")
        
        return {
            "feature": feature_name,
            "success": success,
            "results": results,
            "summary": {
                "backend": results.get("backend", {}).get("status"),
                "frontend": results.get("frontend", {}).get("status"),
                "qa": results.get("qa", {}).get("status"),
            }
        }
    
    def _create_backend_task(self, requirements: dict) -> dict:
        """Create backend task from requirements."""
        task = {"type": "create_endpoint"}
        
        if "api_endpoint" in requirements:
            task["method"] = requirements.get("method", "GET")
            task["path"] = requirements["api_endpoint"]
            task["description"] = requirements.get("description", "")
            task["request_schema"] = requirements.get("request_schema", {})
            task["response_schema"] = requirements.get("response_schema", {})
        
        return task
    
    def _create_frontend_task(self, requirements: dict) -> dict:
        """Create frontend task from requirements."""
        task = {"type": "enhance_template"}
        
        if "page" in requirements:
            task["template_name"] = requirements["page"].lstrip("/").replace("/", "_") + ".html"
            task["feature"] = requirements.get("feature", "enhancement")
            task["details"] = requirements
        
        return task
    
    def _create_qa_task(self, requirements: dict, feature_name: str) -> dict:
        """Create QA task from requirements."""
        task = {"type": "validate_feature"}
        task["feature_name"] = feature_name
        task["test_cases"] = requirements.get("test_cases", [])
        
        return task


# Quick start example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = DevOrchestrator()
    
    # Example: Develop ETF comparison feature
    result = orchestrator.develop_feature(
        feature_name="etf_comparison",
        requirements={
            "backend": {
                "api_endpoint": "/etfs/compare",
                "method": "GET",
                "description": "Compare holdings across multiple ETFs",
                "request_schema": {
                    "query": {
                        "tickers": {"type": "str"},
                        "date": {"type": "str", "default": "None"}
                    }
                },
                "response_schema": {"type": "dict"}
            },
            "frontend": {
                "page": "/compare",
                "feature": "add comparison chart",
                "charts": ["bar", "line"]
            },
            "qa": {
                "test_cases": [
                    {"name": "basic_comparison", "description": "Compare two ETFs"},
                    {"name": "multi_etf", "description": "Compare multiple ETFs"}
                ]
            }
        }
    )
    
    import json
    print("\n" + "="*60)
    print("FEATURE DEVELOPMENT RESULT")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
