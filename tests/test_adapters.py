from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import requests

from app.adapters import get_adapter
from app.adapters.capital_portfolio import CapitalPortfolioAdapter
from app.adapters.fhtrust_etf_html import FhtrustEtfHtmlAdapter
from app.adapters.fsitc_webapi import FsitcWebApiAdapter
from app.adapters.nomura_etfweb import NomuraEtfWebAdapter
from app.adapters.tsit_etf_detail import TsitEtfDetailAdapter
from app.adapters.unified_ezmoney import UnifiedEzmoneyAdapter


class TestGetAdapter:
    """測試適配器工廠函數"""

    def test_get_adapter_returns_correct_adapter(self):
        """測試 get_adapter 返回正確的適配器類型"""
        assert isinstance(get_adapter("capital_portfolio"), CapitalPortfolioAdapter)
        assert isinstance(get_adapter("fhtrust_etf_html"), FhtrustEtfHtmlAdapter)
        # Note: fsitc_webapi is not registered in ADAPTERS dict
        assert isinstance(get_adapter("nomura_etfweb"), NomuraEtfWebAdapter)
        assert isinstance(get_adapter("tsit_etf_detail"), TsitEtfDetailAdapter)
        assert isinstance(get_adapter("unified_ezmoney"), UnifiedEzmoneyAdapter)

    def test_get_adapter_raises_for_unknown_type(self):
        """測試 get_adapter 對未知類型拋出錯誤"""
        try:
            get_adapter("unknown_source")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unsupported source type: unknown_source" in str(e)


class TestTsitEtfDetailAdapter:
    """測試 TSIT ETF 適配器"""

    def test_fetch_success(self):
        """測試 fetch 成功"""
        adapter = TsitEtfDetailAdapter()
        with patch("app.adapters.tsit_etf_detail.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = adapter.fetch("https://example.com", {})
            assert result == "<html>test</html>"

    def test_fetch_raises_on_error(self):
        """測試 fetch 在 HTTP 錯誤時拋出異常"""
        adapter = TsitEtfDetailAdapter()
        with patch("app.adapters.tsit_etf_detail.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection timeout")
            try:
                adapter.fetch("https://example.com", {})
                assert False, "Expected RequestException"
            except requests.RequestException:
                pass

    def test_parse_empty_holdings_raises(self):
        """測試解析空持股時拋出錯誤"""
        adapter = TsitEtfDetailAdapter()
        html = """
        <html>
        <input name="PUB_DATE" value="2026-03-31">
        <table><tr><td>empty</td></tr></table>
        </html>
        """
        try:
            adapter.parse(html, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            # Either table not found or no holdings rows
            assert "Unable to locate stock holdings table" in str(e) or "did not contain any holdings rows" in str(e)

    def test_parse_date_formats(self):
        """測試不同日期格式解析"""
        adapter = TsitEtfDetailAdapter()

        # 測試各種日期格式
        assert adapter._parse_date("2026-03-31") == "2026-03-31"
        assert adapter._parse_date("2026/03/31") == "2026-03-31"
        assert adapter._parse_date("03/31/2026") == "2026-03-31"
        assert adapter._parse_date("03-31-2026") == "2026-03-31"

    def test_parse_date_invalid_raises(self):
        """測試無效日期格式拋出錯誤"""
        adapter = TsitEtfDetailAdapter()
        try:
            adapter._parse_date("invalid-date")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unable to parse TSIT holdings date" in str(e)

    def test_normalize_code(self):
        """測試股票代號正規化"""
        adapter = TsitEtfDetailAdapter()
        assert adapter._normalize_code("2330") == "2330"
        assert adapter._normalize_code("2330.TT") == "2330"
        assert adapter._normalize_code("2330 TT") == "2330"
        assert adapter._normalize_code(" 2330 ") == "2330"

    def test_parse_float_edge_cases(self):
        """測試浮點數解析邊界情況"""
        adapter = TsitEtfDetailAdapter()
        assert adapter._parse_float("10.5") == 10.5
        assert adapter._parse_float("10.5%") == 10.5
        assert adapter._parse_float("1,000") == 1000.0
        assert adapter._parse_float("-") is None
        assert adapter._parse_float("--") is None
        assert adapter._parse_float("N/A") is None
        assert adapter._parse_float("") is None
        assert adapter._parse_float("  ") is None


class TestUnifiedEzmoneyAdapter:
    """測試 Unified Ezmoney 適配器"""

    def test_fetch_success(self):
        """測試 fetch 成功"""
        adapter = UnifiedEzmoneyAdapter()
        with patch("app.adapters.unified_ezmoney.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = adapter.fetch("https://example.com", {})
            assert result == "<html>test</html>"

    def test_parse_missing_data_asset_raises(self):
        """測試缺少 DataAsset 時拋出錯誤"""
        adapter = UnifiedEzmoneyAdapter()
        html = "<html><body>No data here</body></html>"
        try:
            adapter.parse(html, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unable to locate embedded asset data" in str(e)

    def test_parse_missing_stock_block_raises(self):
        """測試缺少股票區塊時拋出錯誤"""
        adapter = UnifiedEzmoneyAdapter()
        html = '''
        <div id="DataAsset" data-content='[{"AssetCode": "BOND", "Details": []}]' style="display:none">
        </div>
        '''
        try:
            adapter.parse(html, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            # Either data asset not found or no stock holdings
            assert "Unable to locate embedded asset data" in str(e) or "did not contain stock holdings details" in str(e)

    def test_parse_float_edge_cases(self):
        """測試浮點數解析邊界情況"""
        adapter = UnifiedEzmoneyAdapter()
        assert adapter._parse_float(10.5) == 10.5
        assert adapter._parse_float("10.5") == 10.5
        assert adapter._parse_float(None) is None
        assert adapter._parse_float("") is None
        assert adapter._parse_float("-") is None
        assert adapter._parse_float("--") is None


class TestFhtrustEtfHtmlAdapter:
    """測試 FH Trust ETF 適配器"""

    def test_fetch_success(self):
        """測試 fetch 成功"""
        adapter = FhtrustEtfHtmlAdapter()
        with patch("app.adapters.fhtrust_etf_html.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status = MagicMock()
            mock_response.ok = True
            mock_response.content = b"PKtest"
            mock_get.return_value = mock_response

            result = adapter.fetch("https://example.com", {"etf_id": "ETF23"})
            assert "html" in result

    def test_parse_empty_holdings_raises(self):
        """測試解析空持股時拋出錯誤"""
        adapter = FhtrustEtfHtmlAdapter()
        html = """
        <html>
        <body>日期：2026-03-30</body>
        <table><tr><td>empty</td></tr></table>
        </html>
        """
        try:
            adapter.parse(html, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            # Either date not found or no holdings rows
            assert "Unable to locate holdings date" in str(e) or "did not contain any holdings rows" in str(e)

    def test_parse_float_edge_cases(self):
        """測試浮點數解析邊界情況"""
        adapter = FhtrustEtfHtmlAdapter()
        assert adapter._parse_float("10.5") == 10.5
        assert adapter._parse_float("10.5%") == 10.5
        assert adapter._parse_float("1,000") == 1000.0
        assert adapter._parse_float("-") is None
        assert adapter._parse_float("") is None
        assert adapter._parse_float("N/A") is None

    def test_normalize_target_date(self):
        """測試目標日期正規化"""
        adapter = FhtrustEtfHtmlAdapter()
        assert adapter._normalize_target_date("2026-03-31").isoformat() == "2026-03-31"
        assert adapter._normalize_target_date("2026/03/31").isoformat() == "2026-03-31"
        assert adapter._normalize_target_date(None) is None
        assert adapter._normalize_target_date("") is None

    def test_normalize_target_date_invalid_raises(self):
        """測試無效日期格式拋出錯誤"""
        adapter = FhtrustEtfHtmlAdapter()
        try:
            adapter._normalize_target_date("invalid-date")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unable to parse target_date" in str(e)


class TestCapitalPortfolioAdapter:
    """測試 Capital Portfolio 適配器"""

    def test_fetch_success(self):
        """測試 fetch 成功"""
        adapter = CapitalPortfolioAdapter()
        with patch("app.adapters.capital_portfolio.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = adapter.fetch("https://example.com", {})
            assert result == "<html>test</html>"

    def test_fetch_with_target_date(self):
        """測試帶目標日期的 fetch"""
        adapter = CapitalPortfolioAdapter()
        with patch("app.adapters.capital_portfolio.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>test</html>"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            adapter.fetch("https://example.com", {"target_date": "2026-03-31"})
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["params"] == {"date": "2026/03/31"}

    def test_parse_missing_date_raises(self):
        """測試缺少日期時拋出錯誤"""
        adapter = CapitalPortfolioAdapter()
        html = "<html><body>No date here</body></html>"
        try:
            adapter.parse(html, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unable to locate holdings date" in str(e)

    def test_parse_missing_stock_section_raises(self):
        """測試缺少股票區塊時拋出錯誤"""
        adapter = CapitalPortfolioAdapter()
        html = """
        <html>
        <input id="condition-date" value="2026-03-31">
        <body>No stock section</body>
        </html>
        """
        try:
            adapter.parse(html, {"today_override": "2026-03-31"})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unable to locate stock holdings section" in str(e)

    def test_parse_float_edge_cases(self):
        """測試浮點數解析邊界情況"""
        adapter = CapitalPortfolioAdapter()
        assert adapter._parse_float("10.5") == 10.5
        assert adapter._parse_float("10.5%") == 10.5
        assert adapter._parse_float("-") is None
        assert adapter._parse_float("") is None
        assert adapter._parse_float("N/A") is None

    def test_parse_date_formats(self):
        """測試不同日期格式解析"""
        adapter = CapitalPortfolioAdapter()
        assert adapter._parse_date("2026-03-31") == "2026-03-31"
        assert adapter._parse_date("2026/03/31") == "2026-03-31"
        assert adapter._parse_date("03/31/2026") == "2026-03-31"


class TestFsitcWebApiAdapter:
    """測試 FSITC Web API 適配器"""

    def test_fetch_success(self):
        """測試 fetch 成功"""
        adapter = FsitcWebApiAdapter()
        with patch("app.adapters.fsitc_webapi.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = '{"d": "[]"}'
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = adapter.fetch("https://example.com", {"fund_id": "00980A"})
            assert result == '{"d": "[]"}'

    def test_fetch_sends_correct_payload(self):
        """測試 fetch 發送正確的 payload"""
        adapter = FsitcWebApiAdapter()
        with patch("app.adapters.fsitc_webapi.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = '{"d": "[]"}'
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            adapter.fetch("https://example.com", {
                "fund_id": "00980A",
                "search_date": "2026-03-31"
            })
            call_args = mock_post.call_args[1]["json"]
            assert call_args["pStrFundID"] == "00980A"
            assert call_args["pStrDate"] == "2026-03-31"

    def test_parse_empty_response_raises(self):
        """測試空回應拋出錯誤"""
        adapter = FsitcWebApiAdapter()
        raw_data = '{"d": "[]"}'
        try:
            adapter.parse(raw_data, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "returned no stock rows" in str(e)

    def test_parse_missing_sdate_raises(self):
        """測試缺少 sdate 時拋出錯誤"""
        adapter = FsitcWebApiAdapter()
        raw_data = json.dumps({"d": json.dumps([{"group": "1", "A": "2330", "D": "1000"}])})
        try:
            adapter.parse(raw_data, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "did not return sdate" in str(e)

    def test_parse_float_edge_cases(self):
        """測試浮點數解析邊界情況"""
        adapter = FsitcWebApiAdapter()
        assert adapter._parse_float(10.5) == 10.5
        assert adapter._parse_float("10.5") == 10.5
        assert adapter._parse_float(None) is None
        assert adapter._parse_float("") is None
        assert adapter._parse_float("-") is None

    def test_parse_valid_response(self):
        """測試解析有效回應"""
        adapter = FsitcWebApiAdapter()
        data = [
            {
                "group": "1",
                "sdate": "2026-03-31",
                "A": "2330",
                "B": "台積電",
                "C": "10.5",
                "D": "1000"
            }
        ]
        raw_data = json.dumps({"d": json.dumps(data)})
        trade_date, holdings = adapter.parse(raw_data, {})

        assert trade_date == "2026-03-31"
        assert len(holdings) == 1
        assert holdings[0].instrument_key == "2330"
        assert holdings[0].quantity == 1000.0


class TestNomuraEtfWebAdapter:
    """測試 Nomura ETF Web 適配器"""

    def test_fetch_success(self):
        """測試 fetch 成功"""
        adapter = NomuraEtfWebAdapter()
        with patch("app.adapters.nomura_etfweb.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = '{"StatusCode": 0}'
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = adapter.fetch("https://example.com", {"fund_no": "00980A"})
            assert result == '{"StatusCode": 0}'

    def test_fetch_sends_correct_payload(self):
        """測試 fetch 發送正確的 payload"""
        adapter = NomuraEtfWebAdapter()
        with patch("app.adapters.nomura_etfweb.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = '{"StatusCode": 0}'
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            adapter.fetch("https://example.com", {
                "fund_no": "00980A",
                "search_date": "2026-03-31"
            })
            call_args = mock_post.call_args[1]["json"]
            assert call_args["FundID"] == "00980A"
            assert call_args["SearchDate"] == "2026-03-31"

    def test_parse_non_success_status_raises(self):
        """測試非成功狀態拋出錯誤"""
        adapter = NomuraEtfWebAdapter()
        raw_data = json.dumps({"StatusCode": 1, "Message": "API Error"})
        try:
            adapter.parse(raw_data, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "API Error" in str(e)

    def test_parse_missing_equity_table_raises(self):
        """測試缺少股票表格時拋出錯誤"""
        adapter = NomuraEtfWebAdapter()
        raw_data = json.dumps({
            "StatusCode": 0,
            "Entries": {
                "Data": {
                    "FundAsset": {"NavDate": "2026/03/31"},
                    "Table": [{"TableTitle": "債券", "Rows": []}]
                }
            }
        })
        try:
            adapter.parse(raw_data, {})
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "did not return an equity holdings table" in str(e)

    def test_parse_float_edge_cases(self):
        """測試浮點數解析邊界情況"""
        adapter = NomuraEtfWebAdapter()
        assert adapter._parse_float("10.5") == 10.5
        assert adapter._parse_float("10.5%") == 10.5
        assert adapter._parse_float("-") is None
        assert adapter._parse_float("") is None
        assert adapter._parse_float("N/A") is None

    def test_normalize_date(self):
        """測試日期正規化"""
        adapter = NomuraEtfWebAdapter()
        assert adapter._normalize_date("2026/03/31") == "2026-03-31"
        assert adapter._normalize_date("2026-03-31") == "2026-03-31"

    def test_normalize_date_invalid_raises(self):
        """測試無效日期格式拋出錯誤"""
        adapter = NomuraEtfWebAdapter()
        try:
            adapter._normalize_date(None)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "did not return NavDate" in str(e)
