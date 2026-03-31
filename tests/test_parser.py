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
    trade_date, holdings = CapitalPortfolioAdapter().parse(html, {"fund_id": "500"})

    assert trade_date == "2026-03-31"
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
            {"fund_id": "500", "target_date": "2026-03-27"},
        )
    except ValueError as exc:
        assert "Requested target_date 2026-03-27 but Capital portfolio page returned 2026-03-31" in str(
            exc
        )
    else:
        raise AssertionError("Expected Capital portfolio parser to reject mismatched target_date")
