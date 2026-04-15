"""Base class for development team agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class DevTaskStatus(Enum):
    """Development task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DevTaskResult:
    """Result of a development task."""
    status: DevTaskStatus
    task_type: str
    description: str
    changes_made: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    test_results: Optional[dict] = None
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "task_type": self.task_type,
            "description": self.description,
            "changes_made": self.changes_made,
            "files_modified": self.files_modified,
            "test_results": self.test_results,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class BaseDevAgent(ABC):
    """
    Base class for all development agents.
    
    Provides common functionality:
    - Project context management
    - File operations
    - Git integration
    - Logging and reporting
    """
    
    def __init__(self, name: str, project_path: Optional[Path] = None):
        """
        Initialize development agent.
        
        Args:
            name: Agent name
            project_path: Path to project root (defaults to ETF tracking system)
        """
        self.name = name
        self.project_path = project_path or Path.home() / "Desktop" / "etf-tracking-system"
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        
        # Setup handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                f'%(asctime)s [{name}] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(handler)
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass
    
    @property
    @abstractmethod
    def responsibilities(self) -> list[str]:
        """List of agent responsibilities."""
        pass
    
    def log_action(self, action: str, details: Optional[str] = None):
        """Log agent action."""
        msg = action
        if details:
            msg += f" - {details}"
        self.logger.info(msg)
    
    def read_file(self, filepath: str) -> str:
        """Read file content from project."""
        full_path = self.project_path / filepath
        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to read {filepath}: {e}")
            raise
    
    def write_file(self, filepath: str, content: str, backup: bool = True):
        """Write content to file with optional backup."""
        full_path = self.project_path / filepath
        
        # Create backup if requested
        if backup and full_path.exists():
            backup_path = full_path.with_suffix(f"{full_path.suffix}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}")
            backup_path.write_text(full_path.read_text(), encoding="utf-8")
            self.log_action(f"Created backup", str(backup_path))
        
        # Write new content
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        self.log_action(f"Written to file", filepath)
    
    def run_command(self, command: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
        """
        Run shell command.
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        import subprocess
        
        self.log_action(f"Running command", command)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or str(self.project_path),
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {command}")
            return -1, "", "Command timed out"
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return -1, "", str(e)
    
    def create_task_result(
        self,
        task_type: str,
        description: str,
        status: DevTaskStatus,
        **kwargs
    ) -> DevTaskResult:
        """Create a task result with timestamp."""
        return DevTaskResult(
            status=status,
            task_type=task_type,
            description=description,
            finished_at=datetime.now().isoformat(),
            **kwargs
        )
    
    @abstractmethod
    def execute_task(self, task: dict) -> DevTaskResult:
        """
        Execute a development task.
        
        Must be implemented by subclasses.
        
        Args:
            task: Task definition
            
        Returns:
            DevTaskResult with outcome
        """
        pass


class FrontendDevAgent(BaseDevAgent):
    """Base class for frontend development agents."""
    
    @property
    def responsibilities(self) -> list[str]:
        return [
            "HTML template development",
            "JavaScript functionality",
            "CSS styling and responsiveness",
            "Chart visualization",
            "User experience improvements",
        ]
    
    def get_template_path(self, template_name: str) -> Path:
        """Get full path to template file."""
        return self.project_path / "templates" / template_name
    
    def get_static_path(self, static_name: str) -> Path:
        """Get full path to static file."""
        return self.project_path / "static" / static_name


class BackendDevAgent(BaseDevAgent):
    """Base class for backend development agents."""
    
    @property
    def responsibilities(self) -> list[str]:
        return [
            "API endpoint development",
            "Service layer implementation",
            "Database operations",
            "Business logic",
            "Security and validation",
        ]
    
    def get_app_path(self, module_name: str = "") -> Path:
        """Get path to app module."""
        base = self.project_path / "app"
        if module_name:
            return base / module_name
        return base
    
    def get_service_path(self, service_name: str) -> Path:
        """Get path to service file."""
        return self.project_path / "app" / "services" / f"{service_name}.py"


class QADevAgent(BaseDevAgent):
    """Base class for QA agents."""
    
    @property
    def responsibilities(self) -> list[str]:
        return [
            "Unit testing",
            "Integration testing",
            "Performance testing",
            "Bug tracking and validation",
            "Code quality analysis",
        ]
    
    def get_test_path(self, test_name: str = "") -> Path:
        """Get path to test file."""
        base = self.project_path / "tests"
        if test_name:
            return base / f"{test_name}.py"
        return base
    
    def run_pytest(self, test_path: Optional[str] = None, verbose: bool = True) -> tuple[int, str]:
        """
        Run pytest on specified tests.
        
        Args:
            test_path: Optional specific test file or directory
            verbose: Show verbose output
            
        Returns:
            Tuple of (exit_code, output)
        """
        cmd = f"python -m pytest"
        
        if verbose:
            cmd += " -v"
        
        if test_path:
            cmd += f" {test_path}"
        
        exit_code, stdout, stderr = self.run_command(cmd)
        return exit_code, stdout + stderr
