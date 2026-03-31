from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from app.models import Holding


class CapitalPortfolioAdapter:
    def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
        params = {}
        target_date = source_config.get("target_date")
        if target_date:
            params["date"] = self._format_request_date(str(target_date))

        response = requests.get(
            source_url,
            params=params or None,
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
        trade_date = self._extract_trade_date(soup, source_config)
        self._assert_target_date(source_config.get("target_date"), trade_date)
        rows = self._extract_stock_rows(soup)

        holdings = [
            Holding(
                instrument_key=row["instrument_key"],
                instrument_name=row["instrument_name"],
                instrument_type="stock",
                quantity=row["quantity"],
                weight=row["weight"],
            )
            for row in rows
        ]
        if not holdings:
            raise ValueError("Capital portfolio page did not contain any holdings rows")

        return trade_date, holdings

    def _extract_trade_date(self, soup: BeautifulSoup, source_config: dict[str, Any]) -> str:
        node = soup.select_one("#condition-date")
        value = node.get("value", "").strip() if node else ""
        if not value:
            raise ValueError("Unable to locate holdings date in Capital portfolio page")
        reported_date = self._parse_date(value)
        return self._normalize_reported_date(reported_date, source_config)

    def _normalize_reported_date(self, reported_date: str, source_config: dict[str, Any]) -> str:
        # Capital portfolio page can expose same-day UI date before holdings are fully finalized.
        if source_config.get("same_day_fallback_to_previous_day", True):
            today_override = source_config.get("today_override")
            if today_override:
                today = datetime.fromisoformat(self._parse_date(str(today_override))).date()
            else:
                today = datetime.now(ZoneInfo("Asia/Taipei")).date()
            parsed = datetime.fromisoformat(reported_date).date()
            if parsed == today:
                return (parsed - timedelta(days=1)).isoformat()
        return reported_date

    def _extract_stock_rows(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        section = soup.select_one("#buyback-stocks-section")
        if not section:
            raise ValueError("Unable to locate stock holdings section in Capital portfolio page")

        rows: list[dict[str, Any]] = []
        for row in section.select(".pct-stock-table-tbody > .tr.show-for-medium"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["div", "td", "th"], recursive=False)]
            if len(cells) < 4:
                continue
            instrument_key = cells[0].strip()
            quantity = self._parse_float(cells[3])
            if not instrument_key or quantity is None:
                continue
            rows.append(
                {
                    "instrument_key": instrument_key,
                    "instrument_name": cells[1].strip(),
                    "weight": self._parse_float(cells[2]),
                    "quantity": quantity,
                }
            )

        if rows:
            return rows

        table = section.find("table")
        if not table:
            raise ValueError("Capital portfolio page did not contain a parseable stock table")

        parsed_rows: list[dict[str, Any]] = []
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) < 4 or cells[0] == "股票代號":
                continue
            quantity = self._parse_float(cells[3])
            if quantity is None:
                continue
            parsed_rows.append(
                {
                    "instrument_key": cells[0].strip(),
                    "instrument_name": cells[1].strip(),
                    "weight": self._parse_float(cells[2]),
                    "quantity": quantity,
                }
            )
        return parsed_rows

    def _format_request_date(self, raw_value: str) -> str:
        return datetime.fromisoformat(self._parse_date(raw_value)).strftime("%Y/%m/%d")

    def _parse_date(self, raw_value: str) -> str:
        value = raw_value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse Capital portfolio date: {raw_value}")

    def _assert_target_date(self, raw_target_date: Any, trade_date: str) -> None:
        if not raw_target_date:
            return
        target_date = self._parse_date(str(raw_target_date))
        if target_date != trade_date:
            raise ValueError(
                f"Requested target_date {target_date} but Capital portfolio page returned {trade_date}"
            )

    def _parse_float(self, value: str) -> Optional[float]:
        text = value.strip().replace(",", "").replace("%", "")
        if not text or text in {"-", "--", "N/A"}:
            return None
        return float(text)
