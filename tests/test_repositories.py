from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from app.models import Holding, HoldingDiff
from app.repositories import (
    _normalize_value,
    _deserialize_etf,
    get_latest_snapshot_count,
    get_latest_crawl_run,
    get_snapshot_metadata,
    get_diffs,
    remove_etf,
    record_crawl_run,
)


class TestNormalizeValue:
    """測試值正規化"""

    def test_normalize_decimal(self):
        """測試 Decimal 正規化"""
        result = _normalize_value(Decimal("10.5"))
        assert result == 10.5

    def test_normalize_datetime(self):
        """測試 datetime 正規化"""
        dt = datetime(2026, 3, 31, 12, 0, 0)
        result = _normalize_value(dt)
        assert "2026-03-31" in result

    def test_normalize_date(self):
        """測試 date 正規化"""
        from datetime import date
        d = date(2026, 3, 31)
        result = _normalize_value(d)
        assert result == "2026-03-31"

    def test_normalize_string(self):
        """測試字串保持不變"""
        result = _normalize_value("test")
        assert result == "test"

    def test_normalize_int(self):
        """測試整數保持不變"""
        result = _normalize_value(100)
        assert result == 100


class TestDeserializeEtf:
    """測試 ETF 反序列化"""

    def test_deserialize_etf_with_json_config(self):
        """測試帶 JSON 配置的 ETF 反序列化"""
        row = {
            "ticker": "00980A",
            "name": "測試 ETF",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": '{"fund_no": "00980A"}',
            "is_active": 1
        }
        result = _deserialize_etf(row)
        assert result["ticker"] == "00980A"
        assert result["source_config"] == {"fund_no": "00980A"}
        assert result["is_active"] is True

    def test_deserialize_etf_with_dict_config(self):
        """測試帶字典配置的 ETF 反序列化"""
        row = {
            "ticker": "00980A",
            "name": "測試 ETF",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": {"fund_no": "00980A"},
            "is_active": 1
        }
        result = _deserialize_etf(row)
        assert result["source_config"] == {"fund_no": "00980A"}

    def test_deserialize_etf_with_none_config(self):
        """測試 None 配置的 ETF 反序列化"""
        row = {
            "ticker": "00980A",
            "name": "測試 ETF",
            "source_type": "test",
            "source_url": "https://example.com",
            "source_config": None,
            "is_active": 0
        }
        result = _deserialize_etf(row)
        assert result["source_config"] == {}
        assert result["is_active"] is False


class TestGetLatestSnapshotCount:
    """測試 get_latest_snapshot_count"""

    def test_get_latest_snapshot_count_empty(self, monkeypatch):
        """測試空數據庫返回 None"""
        mock_row = None
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchone.return_value = mock_row
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        result = get_latest_snapshot_count("00980A")
        assert result is None

    def test_get_latest_snapshot_count_with_data(self, monkeypatch):
        """測試有數據時返回正確計數"""
        mock_row = {"snapshot_count": 10}
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchone.return_value = mock_row
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        result = get_latest_snapshot_count("00980A")
        assert result == 10


class TestGetLatestCrawlRun:
    """測試 get_latest_crawl_run"""

    def test_get_latest_crawl_run_empty(self, monkeypatch):
        """測試空數據庫返回 None"""
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchone.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        result = get_latest_crawl_run("00980A")
        assert result is None


class TestGetSnapshotMetadata:
    """測試 get_snapshot_metadata"""

    def test_get_snapshot_metadata_not_found(self, monkeypatch):
        """測試未找到快照元數據返回 None"""
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchone.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        result = get_snapshot_metadata("00980A", "2026-03-31")
        assert result is None


class TestRecordCrawlRun:
    """測試 record_crawl_run"""

    def test_record_crawl_run_success(self, monkeypatch):
        """測試記錄成功運行"""
        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        record_crawl_run(
            ticker="00980A",
            trigger_type="manual",
            started_at="2026-03-31T10:00:00",
            finished_at="2026-03-31T10:05:00",
            status="success",
            trade_date="2026-03-31"
        )

        mock_connection.execute.assert_called_once()

    def test_record_crawl_run_failed(self, monkeypatch):
        """測試記錄失敗運行"""
        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        record_crawl_run(
            ticker="00980A",
            trigger_type="manual",
            started_at="2026-03-31T10:00:00",
            finished_at="2026-03-31T10:05:00",
            status="failed",
            trade_date=None,
            error_message="Network error"
        )

        call_args = mock_connection.execute.call_args[0]
        assert call_args[1][4] == "failed"
        assert call_args[1][6] == "Network error"


class TestRemoveEtf:
    """測試 remove_etf"""

    def test_remove_etf(self, monkeypatch):
        """測試移除 ETF"""
        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        remove_etf("00980A")

        assert mock_connection.execute.call_count == 4


class TestGetDiffsWithCalculations:
    """測試 get_diffs 的計算"""

    def test_get_diffs_quantity_delta_pct_enter_top10(self, monkeypatch):
        """測試 enter_top10 的 quantity_delta_pct"""
        mock_row = {
            "etf_ticker": "00980A",
            "trade_date": "2026-03-31",
            "instrument_key": "2330",
            "instrument_name": "台積電",
            "change_type": "enter_top10",
            "quantity_delta": 1000,
            "weight_delta": 10.0,
            "prev_quantity": None,
            "curr_quantity": 1000,
            "prev_weight": None,
            "curr_weight": 10.0
        }
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchall.return_value = [mock_row]
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        diffs = get_diffs("00980A", "2026-03-31")
        assert len(diffs) == 1
        assert diffs[0]["quantity_delta_pct"] == 100.0

    def test_get_diffs_quantity_delta_pct_exit_top10(self, monkeypatch):
        """測試 exit_top10 的 quantity_delta_pct"""
        mock_row = {
            "etf_ticker": "00980A",
            "trade_date": "2026-03-31",
            "instrument_key": "2330",
            "instrument_name": "台積電",
            "change_type": "exit_top10",
            "quantity_delta": -1000,
            "weight_delta": -10.0,
            "prev_quantity": 1000,
            "curr_quantity": None,
            "prev_weight": 10.0,
            "curr_weight": None
        }
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchall.return_value = [mock_row]
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        diffs = get_diffs("00980A", "2026-03-31")
        assert len(diffs) == 1
        assert diffs[0]["quantity_delta_pct"] == -100.0

    def test_get_diffs_quantity_delta_pct_increase(self, monkeypatch):
        """測試 increase 的 quantity_delta_pct"""
        mock_row = {
            "etf_ticker": "00980A",
            "trade_date": "2026-03-31",
            "instrument_key": "2330",
            "instrument_name": "台積電",
            "change_type": "increase",
            "quantity_delta": 200,
            "weight_delta": 2.0,
            "prev_quantity": 1000,
            "curr_quantity": 1200,
            "prev_weight": 10.0,
            "curr_weight": 12.0
        }
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchall.return_value = [mock_row]
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        diffs = get_diffs("00980A", "2026-03-31")
        assert len(diffs) == 1
        assert diffs[0]["quantity_delta_pct"] == 20.0

    def test_get_diffs_quantity_lots(self, monkeypatch):
        """測試張數計算"""
        mock_row = {
            "etf_ticker": "00980A",
            "trade_date": "2026-03-31",
            "instrument_key": "2330",
            "instrument_name": "台積電",
            "change_type": "increase",
            "quantity_delta": 2000,
            "weight_delta": 2.0,
            "prev_quantity": 10000,
            "curr_quantity": 12000,
            "prev_weight": 10.0,
            "curr_weight": 12.0
        }
        mock_connection = MagicMock()
        mock_connection.execute.return_value.fetchall.return_value = [mock_row]
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.repositories.get_connection", lambda: mock_context)

        diffs = get_diffs("00980A", "2026-03-31")
        assert diffs[0]["quantity_delta_lots"] == 2.0
        assert diffs[0]["prev_quantity_lots"] == 10.0
        assert diffs[0]["curr_quantity_lots"] == 12.0
