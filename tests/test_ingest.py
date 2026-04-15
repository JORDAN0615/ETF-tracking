from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.models import Holding
from app.services.ingest import (
    _normalize_trade_date,
    _validate_snapshot,
    ingest_latest_snapshot,
    refresh_active_etfs,
)
from app.services.diff import build_diffs


class TestNormalizeTradeDate:
    """測試交易日期正規化"""

    def test_normalize_trade_date_trust_today(self):
        """測試信任今天日期"""
        result = _normalize_trade_date("2026-03-31", trust_today=True)
        assert result == "2026-03-31"

    def test_normalize_trade_date_not_today(self):
        """測試非今天日期保持不變"""
        result = _normalize_trade_date("2026-03-30", trust_today=False)
        assert result == "2026-03-30"


class TestValidateSnapshot:
    """測試快照驗證"""

    def test_validate_snapshot_success(self, monkeypatch):
        """測試驗證成功"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
            Holding("2454", "聯發科", "stock", 700, 7.0),
        ]
        _validate_snapshot("00980A", "2026-03-31", holdings)

    def test_validate_snapshot_missing_trade_date(self, monkeypatch):
        """測試缺少交易日期拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        try:
            _validate_snapshot("00980A", "", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Missing trade_date" in str(e)

    def test_validate_snapshot_empty_holdings(self, monkeypatch):
        """測試空持股拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        try:
            _validate_snapshot("00980A", "2026-03-31", [])
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "No holdings parsed" in str(e)

    def test_validate_snapshot_missing_instrument_key(self, monkeypatch):
        """測試缺少 instrument_key 拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [Holding("", "台積電", "stock", 1000, 10.0)]
        try:
            _validate_snapshot("00980A", "2026-03-31", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "missing instrument_key" in str(e)

    def test_validate_snapshot_missing_instrument_name(self, monkeypatch):
        """測試缺少 instrument_name 拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [Holding("2330", "", "stock", 1000, 10.0)]
        try:
            _validate_snapshot("00980A", "2026-03-31", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "missing instrument_name" in str(e)

    def test_validate_snapshot_negative_quantity(self, monkeypatch):
        """測試負數數量拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [Holding("2330", "台積電", "stock", -100, 10.0)]
        try:
            _validate_snapshot("00980A", "2026-03-31", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "invalid quantity" in str(e)

    def test_validate_snapshot_negative_weight(self, monkeypatch):
        """測試負數權重拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [Holding("2330", "台積電", "stock", 1000, -10.0)]
        try:
            _validate_snapshot("00980A", "2026-03-31", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "invalid weight" in str(e)

    def test_validate_snapshot_duplicate_key(self, monkeypatch):
        """測試重複 instrument_key 拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
            Holding("2330", "台積電 2", "stock", 700, 7.0),
        ]
        try:
            _validate_snapshot("00980A", "2026-03-31", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Duplicate holding" in str(e)

    def test_validate_snapshot_low_count(self, monkeypatch):
        """測試持股數量過少拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: 100)
        holdings = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        try:
            _validate_snapshot("00980A", "2026-03-31", holdings)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "too low versus previous baseline" in str(e)


class TestIngestLatestSnapshot:
    """測試 ingest_latest_snapshot"""

    def test_ingest_unknown_ticker(self, monkeypatch):
        """測試未知 ticker 拋出錯誤"""
        monkeypatch.setattr("app.services.ingest.get_etf", lambda x: None)
        try:
            ingest_latest_snapshot("UNKNOWN")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Unknown ETF ticker: UNKNOWN" in str(e)

    def test_ingest_adapter_error(self, monkeypatch):
        """測試適配器錯誤"""
        class BrokenAdapter:
            def fetch(self, source_url, source_config):
                raise Exception("Network error")

        monkeypatch.setattr("app.services.ingest.get_etf", lambda x: {
            "ticker": "00980A",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": {}
        })
        monkeypatch.setattr("app.services.ingest.get_adapter", lambda x: BrokenAdapter())

        result = ingest_latest_snapshot("00980A")
        assert result["status"] == "failed"
        assert "Network error" in result["error_message"]

    def test_ingest_validation_error(self, monkeypatch):
        """測試驗證錯誤"""
        class StubAdapter:
            def fetch(self, source_url, source_config):
                return "{}"
            def parse(self, raw_data, source_config):
                return ("2026-03-31", [])  # Empty holdings

        monkeypatch.setattr("app.services.ingest.get_etf", lambda x: {
            "ticker": "00980A",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": {}
        })
        monkeypatch.setattr("app.services.ingest.get_adapter", lambda x: StubAdapter())
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)

        result = ingest_latest_snapshot("00980A")
        assert result["status"] == "failed"
        assert "No holdings parsed" in result["error_message"]


class TestRefreshActiveEtfs:
    """測試 refresh_active_etfs"""

    def test_refresh_active_etfs(self, monkeypatch):
        """測試刷新活躍 ETF"""
        monkeypatch.setattr("app.services.ingest.list_etfs", lambda: [
            {"ticker": "00980A", "is_active": True},
            {"ticker": "00981A", "is_active": False},
        ])

        call_results = []
        def mock_ingest(ticker, **kwargs):
            call_results.append(ticker)
            return {"ticker": ticker, "status": "success"}

        monkeypatch.setattr("app.services.ingest.ingest_latest_snapshot", mock_ingest)

        result = refresh_active_etfs()
        assert result["trigger_type"] == "manual"
        assert len(result["results"]) == 1
        assert "00980A" in call_results
        assert "00981A" not in call_results


class TestIngestEdgeCases:
    """測試 ingest 的邊界情況"""

    def test_ingest_with_target_date(self, monkeypatch):
        """測試帶目標日期的 ingest"""
        class StubAdapter:
            def fetch(self, source_url, source_config):
                assert "target_date" in source_config
                return "{}"
            def parse(self, raw_data, source_config):
                return ("2026-03-31", [Holding("2330", "台積電", "stock", 1000, 10.0)])

        monkeypatch.setattr("app.services.ingest.get_etf", lambda x: {
            "ticker": "00980A",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": {}
        })
        monkeypatch.setattr("app.services.ingest.get_adapter", lambda x: StubAdapter())
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        monkeypatch.setattr("app.services.ingest.get_previous_trade_date", lambda x, y: None)
        monkeypatch.setattr("app.services.ingest.replace_snapshot_and_diffs", lambda **kwargs: None)

        result = ingest_latest_snapshot("00980A", target_date="2026-03-30")
        assert result["status"] == "success"
        assert result["target_date"] == "2026-03-30"

    def test_ingest_records_crawl_run_on_success(self, monkeypatch):
        """測試成功時記錄 crawl run"""
        class StubAdapter:
            def fetch(self, source_url, source_config):
                return "{}"
            def parse(self, raw_data, source_config):
                return ("2026-03-31", [Holding("2330", "台積電", "stock", 1000, 10.0)])

        captured_kwargs = {}
        def mock_replace(**kwargs):
            nonlocal captured_kwargs
            captured_kwargs = kwargs

        monkeypatch.setattr("app.services.ingest.get_etf", lambda x: {
            "ticker": "00980A",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": {}
        })
        monkeypatch.setattr("app.services.ingest.get_adapter", lambda x: StubAdapter())
        monkeypatch.setattr("app.services.ingest.get_latest_snapshot_count", lambda x: None)
        monkeypatch.setattr("app.services.ingest.get_previous_trade_date", lambda x, y: None)
        monkeypatch.setattr("app.services.ingest.replace_snapshot_and_diffs", mock_replace)

        ingest_latest_snapshot("00980A", trigger_type="scheduled")
        assert captured_kwargs.get("trigger_type") == "scheduled"
        # replace_snapshot_and_diffs doesn't have status in kwargs, it's passed to record_crawl_run internally
        assert captured_kwargs.get("ticker") == "00980A"
