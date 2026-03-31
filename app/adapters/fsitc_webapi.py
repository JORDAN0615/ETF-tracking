from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import requests

from app.models import Holding


class FsitcWebApiAdapter:
    API_URL = "https://www.fsitc.com.tw/WebAPI.aspx/Get_hd"

    def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
        payload = {
            "pStrFundID": source_config.get("fund_id"),
            "pStrDate": source_config.get("search_date", ""),
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
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw_data: str, source_config: dict[str, Any]) -> tuple[str, list[Holding]]:
        payload = json.loads(raw_data)
        rows = json.loads(payload.get("d") or "[]")
        stock_rows = [row for row in rows if row.get("group") == "1"]
        if not stock_rows:
            raise ValueError("FSITC holdings API returned no stock rows")

        trade_date = self._normalize_date(stock_rows[0].get("sdate"))
        holdings: list[Holding] = []
        for row in stock_rows:
            quantity = self._parse_float(row.get("D"))
            if quantity is None:
                continue
            holdings.append(
                Holding(
                    instrument_key=(row.get("A") or "").strip(),
                    instrument_name=(row.get("B") or "").strip(),
                    instrument_type="stock",
                    quantity=quantity,
                    weight=self._parse_float(row.get("C")),
                )
            )

        if not holdings:
            raise ValueError("FSITC holdings API returned stock rows but none were parsed")

        return trade_date, holdings

    def _normalize_date(self, value: Optional[str]) -> str:
        if not value:
            raise ValueError("FSITC holdings API did not return sdate")
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()

    def _parse_float(self, value: Any) -> Optional[float]:
        if value in (None, "", "-", "--"):
            return None
        return float(str(value).replace(",", "").replace("%", ""))
