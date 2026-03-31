from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Optional

import requests

from app.models import Holding


class NomuraEtfWebAdapter:
    API_URL = "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets"

    def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
        search_date = source_config.get("search_date") or source_config.get("target_date")
        payload = {
            "FundID": source_config.get("fund_no"),
            "SearchDate": search_date,
        }
        response = requests.post(
            self.API_URL,
            json=payload,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
                ),
                "Referer": source_url,
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw_data: str, source_config: dict[str, Any]) -> tuple[str, list[Holding]]:
        payload = json.loads(raw_data)
        if payload.get("StatusCode") != 0:
            raise ValueError(
                payload.get("Message") or "Nomura holdings API returned a non-success status"
            )

        entries = payload.get("Entries") or {}
        data = entries.get("Data") or {}
        fund_asset = data.get("FundAsset") or {}
        trade_date = self._normalize_date(fund_asset.get("NavDate"))

        target_table = None
        for table in data.get("Table") or []:
            if table.get("TableTitle") == "股票":
                target_table = table
                break

        if target_table is None:
            raise ValueError("Nomura holdings API did not return an equity holdings table")

        holdings: list[Holding] = []
        for row in target_table.get("Rows") or []:
            if len(row) < 4:
                continue

            instrument_key = row[0]
            instrument_name = row[1] or instrument_key
            quantity = self._parse_float(row[2])
            weight = self._parse_float(row[3])
            if quantity is None:
                continue

            holdings.append(
                Holding(
                    instrument_key=instrument_key,
                    instrument_name=instrument_name,
                    instrument_type="stock",
                    quantity=quantity,
                    weight=weight,
                )
            )

        if not holdings:
            raise ValueError("Nomura holdings API returned no holdings rows")

        return trade_date, holdings

    def _normalize_date(self, value: Optional[str]) -> str:
        if not value:
            raise ValueError("Nomura holdings API did not return NavDate")
        return datetime.strptime(value.replace("/", "-"), "%Y-%m-%d").date().isoformat()

    def _parse_float(self, value: str) -> Optional[float]:
        text = value.strip().replace(",", "").replace("%", "")
        if not text or text in {"-", "--", "N/A"}:
            return None
        return float(text)
