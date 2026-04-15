"""Export services for ETF tracking data."""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Optional

from fastapi import Response


def export_holdings_csv(holdings: list[dict]) -> Response:
    """Export holdings data as CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=holdings[0].keys())
    writer.writeheader()
    writer.writerows(holdings)
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=holdings.csv"}
    )


def export_diffs_csv(diffs: list[dict]) -> Response:
    """Export holding diffs as CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=diffs[0].keys())
    writer.writeheader()
    writer.writerows(diffs)
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=diffs.csv"}
    )


def export_holdings_json(holdings: list[dict]) -> Response:
    """Export holdings data as JSON."""
    content = json.dumps(holdings, ensure_ascii=False, indent=2)
    
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=holdings.json"}
    )


def export_diffs_json(diffs: list[dict]) -> Response:
    """Export holding diffs as JSON."""
    content = json.dumps(diffs, ensure_ascii=False, indent=2)
    
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=diffs.json"}
    )


def export_etf_summary_json(etfs: list[dict]) -> Response:
    """Export ETF summary as JSON."""
    content = json.dumps(etfs, ensure_ascii=False, indent=2)
    
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=etf_summary.json"}
    )


def export_statistics_json(stats: dict[str, Any]) -> Response:
    """Export statistics as JSON."""
    content = json.dumps(stats, ensure_ascii=False, indent=2)
    
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=statistics.json"}
    )


# Excel export using openpyxl (optional, requires additional dependency)
def _try_import_openpyxl():
    """Try to import openpyxl for Excel export."""
    try:
        from openpyxl import Workbook
        return Workbook
    except ImportError:
        return None


def export_holdings_excel(holdings: list[dict]) -> Optional[Response]:
    """Export holdings data as Excel file."""
    Workbook = _try_import_openpyxl()
    if Workbook is None:
        return None
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Holdings"
    
    # Write header
    headers = list(holdings[0].keys()) if holdings else []
    ws.append(headers)
    
    # Write data
    for row in holdings:
        ws.append([row.get(h) for h in headers])
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=holdings.xlsx"}
    )
