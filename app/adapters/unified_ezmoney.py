from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any, Optional

import requests

from app.models import Holding


class UnifiedEzmoneyAdapter:
    MAX_HOLDINGS = 50
    DATA_ASSET_PATTERN = re.compile(
        r'<div[^>]*id="DataAsset"[^>]*data-content="(.*?)"[^>]*style=',
        re.S,
    )

    def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
        response = requests.get(
            source_url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw_data: str, source_config: dict[str, Any]) -> tuple[str, list[Holding]]:
        match = self.DATA_ASSET_PATTERN.search(raw_data)
        if not match:
            raise ValueError("Unable to locate embedded asset data in Unified ETF page")

        asset_data = json.loads(html.unescape(match.group(1)))
        stock_block = next(
            (item for item in asset_data if item.get("AssetCode") == "ST" and item.get("Details")),
            None,
        )
        if not stock_block:
            raise ValueError("Unified ETF page did not contain stock holdings details")

        details = stock_block["Details"]
        first_trade_date = details[0].get("TranDate")
        if not first_trade_date:
            raise ValueError("Unified ETF holdings details did not contain TranDate")
        trade_date = datetime.fromisoformat(first_trade_date).date().isoformat()

        holdings: list[Holding] = []
        for item in details:
            quantity = self._parse_float(item.get("Share"))
            if quantity is None:
                continue

            holdings.append(
                Holding(
                    instrument_key=(item.get("DetailCode") or "").strip(),
                    instrument_name=(item.get("DetailName") or "").strip(),
                    instrument_type="stock",
                    quantity=quantity,
                    weight=self._parse_float(item.get("NavRate")),
                )
            )

        if not holdings:
            raise ValueError("Unified ETF holdings block was present but no rows were parsed")

        holdings = sorted(
            holdings,
            key=lambda item: (
                item.weight is None,
                -(item.weight or 0.0),
                -(item.quantity or 0.0),
                item.instrument_key,
            ),
        )[: self.MAX_HOLDINGS]

        return trade_date, holdings

    def _parse_float(self, value: Any) -> Optional[float]:
        if value in (None, "", "-", "--"):
            return None
        return float(value)
