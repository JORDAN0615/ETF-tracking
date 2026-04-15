# Agents Package

This package contains autonomous agents for the ETF Tracking System.

## Structure

```
agents/
├── __init__.py                 # Package initialization
├── base.py                     # Base agent class
├── orchestrator.py             # Main orchestration logic
├── fetchers/                   # Data fetching agents
│   ├── __init__.py
│   ├── nomura_agent.py
│   ├── capital_agent.py
│   ├── fhtrust_agent.py
│   ├── tsit_agent.py
│   └── unified_agent.py
├── analyzers/                  # Analysis agents
│   ├── __init__.py
│   ├── statistics_agent.py
│   ├── trend_agent.py
│   └── alert_agent.py
└── maintainers/                # Maintenance agents
    ├── __init__.py
    ├── health_check_agent.py
    ├── backup_agent.py
    └── migration_agent.py
```

## Usage

```python
from agents import ETFManagerAgent

# Initialize manager
manager = ETFManagerAgent()

# Refresh all ETFs
result = manager.refresh_all()

# Refresh single ETF
result = manager.refresh_single("00992A")

# Run analysis
stats = manager.analyze_statistics("00992A")
```

## Agent Communication

Agents communicate through:
1. Direct function calls (synchronous)
2. Delegate task (asynchronous, via Hermes)
3. Shared database (state persistence)
