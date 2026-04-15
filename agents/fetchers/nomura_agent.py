"""Nomura Trust & Banking ETF Data Fetching Agent."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.base import FetchingAgent, AgentResult, AgentStatus
from app.adapters import get_adapter


class NomuraAgent(FetchingAgent):
    """
    Agent for fetching ETF data from Nomura Trust & Banking.
    
    Supports ETFs:
    - 00992A: 群益台灣優質高息 ETF
    - 00981A: 群益半導體參與式 ETF
    
    Uses the existing nomura_etfweb adapter for data fetching.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize NomuraAgent."""
        super().__init__("NomuraAgent", logger)
    
    @property
    def description(self) -> str:
        return "Fetches ETF holdings data from Nomura Trust & Banking API"
    
    @property
    def supported_tickers(self) -> list[str]:
        return ["00992A", "00981A"]
    
    def fetch(self, ticker: str, target_date: Optional[str] = None) -> AgentResult:
        """
        Fetch ETF holdings from Nomura source.
        
        Args:
            ticker: ETF ticker (00992A or 00981A)
            target_date: Optional target date (YYYY-MM-DD)
            
        Returns:
            AgentResult with holdings data
        """
        self.log_execution(f"Starting fetch for {ticker}", {"target_date": target_date})
        
        try:
            # Validate ticker
            if ticker not in self.supported_tickers:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error=f"Unsupported ticker: {ticker}. Supported: {self.supported_tickers}",
                )
            
            # Get adapter
            adapter = get_adapter("nomura_etfweb")
            
            # Prepare source config
            from app.repositories import get_etf
            etf_info = get_etf(ticker)
            
            if not etf_info:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error=f"ETF {ticker} not found in database",
                )
            
            source_config = dict(etf_info.get("source_config", {}))
            if target_date:
                source_config["target_date"] = target_date
            
            self.log_execution("Fetching raw data", {"url": etf_info["source_url"]})
            
            # Fetch raw data
            raw_data = adapter.fetch(etf_info["source_url"], source_config)
            
            # Parse data
            self.log_execution("Parsing data")
            trade_date, holdings = adapter.parse(raw_data, source_config)
            
            # Normalize trade date (if needed)
            from app.services.ingest import _normalize_trade_date
            trust_today = source_config.get("trust_today", False)
            trade_date = _normalize_trade_date(trade_date, trust_today=trust_today)
            
            # Validate holdings
            if not holdings:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error="No holdings parsed from source data",
                )
            
            self.log_execution(f"Successfully fetched {len(holdings)} holdings", {"trade_date": trade_date})
            
            # Convert to standard format
            holdings_data = [
                {
                    "instrument_key": h.instrument_key,
                    "instrument_name": h.instrument_name,
                    "instrument_type": h.instrument_type,
                    "quantity": h.quantity,
                    "weight": h.weight,
                }
                for h in holdings
            ]
            
            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "ticker": ticker,
                    "trade_date": trade_date,
                    "holdings": holdings_data,
                    "source": "nomura",
                    "holding_count": len(holdings_data),
                },
            )
            
        except Exception as e:
            self.logger.error(f"Fetch failed: {e}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                error=str(e),
            )


# Standalone execution for testing
if __name__ == "__main__":
    import json
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create agent
    agent = NomuraAgent()
    
    # Test fetch
    result = agent.fetch("00992A")
    
    print("\n" + "="*60)
    print("FETCH RESULT")
    print("="*60)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
