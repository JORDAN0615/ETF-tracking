from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ETF:
    ticker: str
    name: str
    source_type: str
    source_url: str
    source_config: dict[str, Any]
    is_active: bool = True


@dataclass(frozen=True)
class Holding:
    instrument_key: str
    instrument_name: str
    instrument_type: str
    quantity: float
    weight: Optional[float]


@dataclass(frozen=True)
class HoldingDiff:
    instrument_key: str
    instrument_name: str
    change_type: str
    quantity_delta: float
    weight_delta: Optional[float]
    prev_quantity: Optional[float]
    curr_quantity: Optional[float]
    prev_weight: Optional[float]
    curr_weight: Optional[float]
