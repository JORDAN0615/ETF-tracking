from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from app.models import Holding


class TsitEtfDetailAdapter:
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
        trade_date = self._extract_trade_date(soup)
        self._assert_target_date(source_config.get("target_date"), trade_date)
        table = self._find_stock_table(soup)

        holdings: list[Holding] = []
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) < 4:
                continue
            if cells[0] == "代號":
                continue

            instrument_key = self._normalize_code(cells[0])
            quantity = self._parse_float(cells[2])
            weight = self._parse_float(cells[3])
            if not instrument_key or quantity is None:
                continue

            holdings.append(
                Holding(
                    instrument_key=instrument_key,
                    instrument_name=cells[1].strip(),
                    instrument_type="stock",
                    quantity=quantity,
                    weight=weight,
                )
            )

        if not holdings:
            raise ValueError("TSIT ETF page did not contain any holdings rows")

        return trade_date, holdings

    def _extract_trade_date(self, soup: BeautifulSoup) -> str:
        for selector in ('input[name="PUB_DATE"]', "#PUB_DATE"):
            node = soup.select_one(selector)
            value = node.get("value", "").strip() if node else ""
            if value:
                return self._parse_date(value)
        raise ValueError("Unable to locate holdings date in TSIT ETF page")

    def _find_stock_table(self, soup: BeautifulSoup):
        for table in soup.find_all("table"):
            headers = [cell.get_text(" ", strip=True) for cell in table.find_all(["th", "td"])]
            joined = " ".join(headers)
            if "代號" in joined and "名稱" in joined and "股數" in joined and "持股權重" in joined:
                return table
        raise ValueError("Unable to locate stock holdings table in TSIT ETF page")

    def _normalize_code(self, raw_code: str) -> str:
        code = raw_code.strip().replace(".TT", "").replace(" TT", "")
        if code.upper().endswith("TT"):
            code = code[:-2]
        return code.strip()

    def _parse_date(self, raw_value: str) -> str:
        value = raw_value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse TSIT holdings date: {raw_value}")

    def _assert_target_date(self, raw_target_date: Any, trade_date: str) -> None:
        if not raw_target_date:
            return
        target_date = self._parse_date(str(raw_target_date))
        if target_date != trade_date:
            raise ValueError(
                f"Requested target_date {target_date} but TSIT page returned {trade_date}"
            )

    def _parse_float(self, value: str) -> Optional[float]:
        text = value.strip().replace(",", "").replace("%", "")
        if not text or text in {"-", "--", "N/A"}:
            return None
        try:
            return float(text)
        except ValueError:
            return None
