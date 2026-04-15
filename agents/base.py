"""Base class for all ETF Tracking Agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AgentResult:
    """Standard result format for all agents."""
    status: AgentStatus
    data: Optional[dict] = None
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "execution_time_ms": self.execution_time_ms,
        }


class BaseAgent(ABC):
    """
    Base class for all ETF tracking agents.
    
    Provides common functionality:
    - Logging
    - Error handling
    - Result formatting
    - Status tracking
    """
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize agent.
        
        Args:
            name: Unique agent name
            logger: Optional logger instance
        """
        self.name = name
        self.logger = logger or logging.getLogger(self.name)
        self._status = AgentStatus.PENDING
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass
    
    @property
    def status(self) -> AgentStatus:
        """Current agent status."""
        return self._status
    
    @status.setter
    def status(self, value: AgentStatus):
        """Update agent status."""
        self._status = value
        self.logger.debug(f"Status changed: {self._status.value}")
    
    @abstractmethod
    def execute(self, **kwargs) -> AgentResult:
        """
        Execute agent task.
        
        Must be implemented by subclasses.
        
        Returns:
            AgentResult with execution outcome
        """
        pass
    
    def run_with_retry(
        self,
        max_retries: int = 3,
        backoff_seconds: int = 30,
        **kwargs
    ) -> AgentResult:
        """
        Execute with automatic retry on failure.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_seconds: Base backoff time in seconds
            **kwargs: Arguments passed to execute()
            
        Returns:
            AgentResult from final execution
        """
        import time
        
        last_error = None
        
        for attempt in range(max_retries):
            self.logger.info(f"Execution attempt {attempt + 1}/{max_retries}")
            
            try:
                result = self.execute(**kwargs)
                
                if result.status == AgentStatus.SUCCESS:
                    self.logger.info("Execution successful")
                    return result
                
                last_error = result.error
                self.logger.warning(f"Execution failed: {result.error}")
                
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Exception during execution: {e}")
            
            # Sleep before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = backoff_seconds * (attempt + 1)
                self.logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        # All retries exhausted
        self.logger.error(f"All {max_retries} attempts failed")
        return AgentResult(
            status=AgentStatus.FAILED,
            error=f"Failed after {max_retries} attempts. Last error: {last_error}",
        )
    
    def validate_result(self, result: AgentResult) -> bool:
        """
        Validate agent result.
        
        Override in subclass for custom validation.
        
        Args:
            result: AgentResult to validate
            
        Returns:
            True if valid, False otherwise
        """
        if result.status == AgentStatus.FAILED:
            return False
        
        if result.data is None:
            self.logger.warning("Result has no data")
            return False
        
        return True
    
    def log_execution(self, action: str, details: Optional[dict] = None):
        """
        Log agent execution event.
        
        Args:
            action: Action being performed
            details: Optional additional details
        """
        log_msg = f"{action}"
        if details:
            log_msg += f" - {details}"
        
        self.logger.info(log_msg)


class FetchingAgent(BaseAgent, ABC):
    """Base class for data fetching agents."""
    
    @property
    @abstractmethod
    def supported_tickers(self) -> list[str]:
        """List of ETF tickers this agent can fetch."""
        pass
    
    @abstractmethod
    def fetch(self, ticker: str, target_date: Optional[str] = None) -> AgentResult:
        """
        Fetch ETF holdings data.
        
        Args:
            ticker: ETF ticker symbol
            target_date: Optional target date (YYYY-MM-DD)
            
        Returns:
            AgentResult with holdings data
        """
        pass
    
    def execute(self, **kwargs) -> AgentResult:
        """Delegate to fetch() method."""
        ticker = kwargs.get("ticker")
        target_date = kwargs.get("target_date")
        
        if not ticker:
            return AgentResult(
                status=AgentStatus.FAILED,
                error="Missing required parameter: ticker",
            )
        
        return self.fetch(ticker, target_date)


class AnalysisAgent(BaseAgent, ABC):
    """Base class for analysis agents."""
    
    @abstractmethod
    def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """
        Perform analysis on ETF data.
        
        Args:
            ticker: ETF ticker symbol
            **kwargs: Analysis-specific parameters
            
        Returns:
            AgentResult with analysis data
        """
        pass
    
    def execute(self, **kwargs) -> AgentResult:
        """Delegate to analyze() method."""
        ticker = kwargs.get("ticker")
        
        if not ticker:
            return AgentResult(
                status=AgentStatus.FAILED,
                error="Missing required parameter: ticker",
            )
        
        return self.analyze(ticker, **{k: v for k, v in kwargs.items() if k != "ticker"})


class MaintenanceAgent(BaseAgent, ABC):
    """Base class for maintenance agents."""
    
    @abstractmethod
    def run_maintenance(self, **kwargs) -> AgentResult:
        """
        Run maintenance task.
        
        Args:
            **kwargs: Task-specific parameters
            
        Returns:
            AgentResult with maintenance outcome
        """
        pass
    
    def execute(self, **kwargs) -> AgentResult:
        """Delegate to run_maintenance() method."""
        return self.run_maintenance(**kwargs)
