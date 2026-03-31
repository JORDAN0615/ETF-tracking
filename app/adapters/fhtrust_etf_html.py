from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any, Optional
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from app.models import Holding


class FhtrustEtfHtmlAdapter:
    DATE_PATTERN = re.compile(r"日期[：:]\s*(\d{4}/\d{2}/\d{2})")
    XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    def fetch(self, source_url: str, source_config: dict[str, Any]) -> dict[str, Any]:
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
        html = response.text

        excel_bytes: bytes | None = None
        excel_path = self._extract_assets_excel_path(html, source_config)
        if excel_path:
            excel_url = requests.compat.urljoin(source_url, excel_path)
            excel_response = requests.get(
                excel_url,
                timeout=15,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
                    )
                },
            )
            if excel_response.ok and excel_response.content:
                excel_bytes = excel_response.content

        return {"html": html, "excel_bytes": excel_bytes}

    def parse(self, raw_data: Any, source_config: dict[str, Any]) -> tuple[str, list[Holding]]:
        if isinstance(raw_data, dict):
            html = raw_data.get("html", "")
            excel_bytes = raw_data.get("excel_bytes")
        else:
            html = str(raw_data)
            excel_bytes = None

        if excel_bytes:
            try:
                trade_date, holdings = self._parse_assets_excel(excel_bytes)
                self._assert_target_date(source_config.get("target_date"), trade_date)
                return trade_date, holdings
            except Exception:
                pass

        soup = BeautifulSoup(html, "html.parser")
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

        self._assert_target_date(source_config.get("target_date"), trade_date)
        return trade_date, holdings

    def _extract_assets_excel_path(self, html: str, source_config: dict[str, Any]) -> Optional[str]:
        etf_id = source_config.get("etf_id")
        target_date = self._normalize_target_date(source_config.get("target_date"))
        if etf_id and target_date:
            return f"/api/assetsExcel/{etf_id}/{target_date.strftime('%Y%m%d')}"

        match = re.search(r'href=["\'](/api/assetsExcel/[^"\']+)["\']', html)
        if match:
            return match.group(1)
        if not etf_id:
            return None
        date_matches = self.DATE_PATTERN.findall(html)
        if not date_matches:
            return None
        latest = max(datetime.strptime(value, "%Y/%m/%d").date() for value in date_matches)
        return f"/api/assetsExcel/{etf_id}/{latest.strftime('%Y%m%d')}"

    def _parse_assets_excel(self, excel_bytes: bytes) -> tuple[str, list[Holding]]:
        with ZipFile(BytesIO(excel_bytes)) as workbook:
            sheet_xml = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
            shared_strings = self._load_shared_strings(workbook)
            rows = sheet_xml.findall(".//x:sheetData/x:row", self.XLSX_NS)

        trade_date: Optional[str] = None
        holdings: list[Holding] = []
        in_holdings = False

        for row in rows:
            cells = self._row_values(row, shared_strings)
            if not cells:
                continue

            if not trade_date:
                row_text = " ".join(cells)
                date_matches = self.DATE_PATTERN.findall(row_text)
                if date_matches:
                    trade_date = max(
                        datetime.strptime(value, "%Y/%m/%d").date() for value in date_matches
                    ).isoformat()

            if len(cells) >= 5 and cells[0] == "證券代號" and cells[1] == "證券名稱":
                in_holdings = True
                continue

            if not in_holdings:
                continue

            instrument_key = cells[0].strip()
            instrument_name = cells[1].strip()
            quantity = self._parse_float(cells[2])
            weight = self._parse_float(cells[4])

            if not instrument_key or not instrument_name or quantity is None:
                if holdings:
                    break
                continue

            if not re.match(r"^\d+[A-Za-z]?$", instrument_key):
                if holdings:
                    break
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

        if not trade_date:
            raise ValueError("Unable to locate holdings date in FH Trust assets excel")
        if not holdings:
            raise ValueError("FH Trust assets excel did not contain any holdings rows")
        return trade_date, holdings

    def _normalize_target_date(self, raw_target_date: Any) -> Optional[date]:
        if not raw_target_date:
            return None
        value = str(raw_target_date).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse target_date: {raw_target_date}")

    def _assert_target_date(self, raw_target_date: Any, trade_date: str) -> None:
        target_date = self._normalize_target_date(raw_target_date)
        if not target_date:
            return
        if trade_date != target_date.isoformat():
            raise ValueError(
                f"Requested target_date {target_date.isoformat()} but FH Trust page returned {trade_date}"
            )

    def _load_shared_strings(self, workbook: ZipFile) -> list[str]:
        try:
            shared_xml = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        except KeyError:
            return []

        values: list[str] = []
        for item in shared_xml.findall("x:si", self.XLSX_NS):
            texts = [node.text or "" for node in item.findall(".//x:t", self.XLSX_NS)]
            values.append("".join(texts))
        return values

    def _row_values(self, row: ET.Element, shared_strings: list[str]) -> list[str]:
        values: list[str] = []
        for cell in row.findall("x:c", self.XLSX_NS):
            value = self._cell_value(cell, shared_strings)
            if value is not None:
                values.append(value.strip())
        return values

    def _cell_value(self, cell: ET.Element, shared_strings: list[str]) -> Optional[str]:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            text_nodes = cell.findall(".//x:t", self.XLSX_NS)
            return "".join(node.text or "" for node in text_nodes)

        value_node = cell.find("x:v", self.XLSX_NS)
        if value_node is None or value_node.text is None:
            return None
        raw = value_node.text
        if cell_type == "s":
            idx = int(raw)
            return shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
        return raw

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
