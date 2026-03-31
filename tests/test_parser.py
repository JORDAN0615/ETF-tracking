from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from app.adapters.capital_portfolio import CapitalPortfolioAdapter
from app.adapters.fhtrust_etf_html import FhtrustEtfHtmlAdapter
from app.adapters.nomura_etfweb import NomuraEtfWebAdapter
from app.adapters.tsit_etf_detail import TsitEtfDetailAdapter
from app.adapters.unified_ezmoney import UnifiedEzmoneyAdapter


def test_parse_holdings(fixtures_dir) -> None:
    payload = (fixtures_dir / "nomura_fund_assets_sample.json").read_text(encoding="utf-8")
    trade_date, holdings = NomuraEtfWebAdapter().parse(payload, {"fund_no": "00980A"})

    assert trade_date == "2026-03-30"
    assert len(holdings) == 2
    assert holdings[0].instrument_key == "2330"
    assert holdings[0].quantity == 583000
    assert holdings[0].weight == 8.67


def test_parse_unified_holdings(fixtures_dir) -> None:
    html = (fixtures_dir / "unified_data_asset_sample.html").read_text(encoding="utf-8")
    trade_date, holdings = UnifiedEzmoneyAdapter().parse(html, {"fund_code": "49YTW"})

    assert trade_date == "2026-03-30"
    assert len(holdings) == 2
    assert holdings[0].instrument_key == "2330"
    assert holdings[0].quantity == 5023000
    assert holdings[0].weight == 8.95


def test_parse_fhtrust_holdings(fixtures_dir) -> None:
    html = (fixtures_dir / "fhtrust_stockhold_sample.html").read_text(encoding="utf-8")
    trade_date, holdings = FhtrustEtfHtmlAdapter().parse(html, {"etf_id": "ETF23"})

    assert trade_date == "2026-03-27"
    assert len(holdings) == 2
    assert holdings[0].instrument_key == "2330"
    assert holdings[0].quantity == 2730000
    assert holdings[0].weight == 17.505


def test_parse_fhtrust_assets_excel() -> None:
    excel_bytes = _build_fhtrust_excel(
        date="2026/03/31",
        rows=[
            ("2330", "台灣積體", "2730000", "4968600000", "17.505%"),
            ("2383", "台光電子", "800000", "2328000000", "8.202%"),
            ("8299", "群聯電子", "1300000", "2034500000", "7.168%"),
        ],
    )
    raw_data = {
        "html": "<html><body>日期：2026/03/30</body></html>",
        "excel_bytes": excel_bytes,
    }
    trade_date, holdings = FhtrustEtfHtmlAdapter().parse(raw_data, {"etf_id": "ETF23"})

    assert trade_date == "2026-03-31"
    assert len(holdings) == 3
    assert holdings[0].instrument_key == "2330"
    assert holdings[0].quantity == 2730000
    assert holdings[0].weight == 17.505


def test_parse_tsit_holdings(fixtures_dir) -> None:
    html = (fixtures_dir / "tsit_00987a_sample.html").read_text(encoding="utf-8")
    trade_date, holdings = TsitEtfDetailAdapter().parse(html, {"fund_no": "00987A"})

    assert trade_date == "2026-03-31"
    assert len(holdings) == 2
    assert holdings[0].instrument_key == "2330"
    assert holdings[0].instrument_name == "台積電"
    assert holdings[0].quantity == 677000
    assert holdings[0].weight == 5.91


def test_parse_capital_portfolio_holdings(fixtures_dir) -> None:
    html = (fixtures_dir / "capital_00992a_portfolio_sample.html").read_text(encoding="utf-8")
    trade_date, holdings = CapitalPortfolioAdapter().parse(
        html,
        {"fund_id": "500", "today_override": "2026-03-31"},
    )

    assert trade_date == "2026-03-30"
    assert len(holdings) == 3
    assert holdings[0].instrument_key == "2330"
    assert holdings[0].instrument_name == "台積電"
    assert holdings[0].quantity == 677000
    assert holdings[0].weight == 5.91


def test_capital_portfolio_rejects_date_mismatch(fixtures_dir) -> None:
    html = (fixtures_dir / "capital_00992a_portfolio_sample.html").read_text(encoding="utf-8")

    try:
        CapitalPortfolioAdapter().parse(
            html,
            {
                "fund_id": "500",
                "target_date": "2026-03-27",
                "today_override": "2026-03-31",
            },
        )
    except ValueError as exc:
        assert "Requested target_date 2026-03-27 but Capital portfolio page returned 2026-03-30" in str(
            exc
        )
    else:
        raise AssertionError("Expected Capital portfolio parser to reject mismatched target_date")


def _build_fhtrust_excel(date: str, rows: list[tuple[str, str, str, str, str]]) -> bytes:
    shared_strings = [
        "復華台灣未來50主動式ETF基金（證券代碼：00991A）",
        f"日期: {date}",
        "證券代號",
        "證券名稱",
        "股數",
        "金額",
        "權重(%)",
    ]
    for row in rows:
        shared_strings.extend(row)

    sst_items = "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">{sst_items}</sst>'
    )

    row_xml = [
        '<row r="1"><c r="A1" t="s"><v>0</v></c></row>',
        '<row r="3"><c r="A3" t="s"><v>1</v></c></row>',
        '<row r="11">'
        '<c r="A11" t="s"><v>2</v></c>'
        '<c r="B11" t="s"><v>3</v></c>'
        '<c r="C11" t="s"><v>4</v></c>'
        '<c r="D11" t="s"><v>5</v></c>'
        '<c r="E11" t="s"><v>6</v></c>'
        "</row>",
    ]
    base_idx = 7
    for i, _ in enumerate(rows):
        r = 12 + i
        idx = base_idx + i * 5
        row_xml.append(
            f'<row r="{r}">'
            f'<c r="A{r}" t="s"><v>{idx}</v></c>'
            f'<c r="B{r}" t="s"><v>{idx + 1}</v></c>'
            f'<c r="C{r}" t="s"><v>{idx + 2}</v></c>'
            f'<c r="D{r}" t="s"><v>{idx + 3}</v></c>'
            f'<c r="E{r}" t="s"><v>{idx + 4}</v></c>'
            "</row>"
        )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(row_xml)}</sheetData></worksheet>"
    )

    output = BytesIO()
    with ZipFile(output, "w") as workbook:
        workbook.writestr("xl/sharedStrings.xml", shared_xml)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()
