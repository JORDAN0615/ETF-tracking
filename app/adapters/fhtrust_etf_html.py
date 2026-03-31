from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from app.models import Holding


class FhtrustEtfHtmlAdapter:
    DATE_PATTERN = re.compile(r"日期[：:]\s*(\d{4}/\d{2}/\d{2})")

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
        soup = BeautifulSoup(raw_data, "html.parser")
        text = soup.get_text(" ", strip=True)
        trade_date = self._extract_trade_date(text)
        table = self._find_stock_table(soup)

        holdings: list[Holding] = []
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) < 5:
                continue

            instrument_key = cells[0]
            instrument_name = cells[1]
            quantity = self._parse_float(cells[2])
            weight = self._parse_float(cells[4])
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
            raise ValueError("FH Trust ETF page did not contain any holdings rows")

        return trade_date, holdings

    def _extract_trade_date(self, text: str) -> str:
        matches = self.DATE_PATTERN.findall(text)
        if not matches:
            raise ValueError("Unable to locate holdings date in FH Trust ETF page")
        latest = max(datetime.strptime(value, "%Y/%m/%d").date() for value in matches)
        return latest.isoformat()

    def _find_stock_table(self, soup: BeautifulSoup):
        for table in soup.find_all("table"):
            headers = [cell.get_text(" ", strip=True) for cell in table.find_all(["th", "td"])]
            joined = " ".join(headers)
            if "證券 代號" in joined and "證券名稱" in joined and "權重" in joined:
                return table
        raise ValueError("Unable to locate stock holdings table in FH Trust ETF page")

    def _parse_float(self, value: str) -> Optional[float]:
        text = value.strip().replace(",", "").replace("%", "")
        if not text or text in {"-", "--", "N/A"}:
            return None
        return float(text)
