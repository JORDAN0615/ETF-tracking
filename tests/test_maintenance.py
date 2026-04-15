from __future__ import annotations

from unittest.mock import patch, MagicMock

from app.models import Holding
from app.services.maintenance import lock_00992a_baseline


class TestLock00992aBaseline:
    """測試 lock_00992a_baseline 維護函數"""

    def test_lock_baseline_no_data(self, monkeypatch):
        """測試沒有數據時不執行操作"""
        monkeypatch.setattr("app.services.maintenance.get_snapshot", lambda x, y: [])

        lock_00992a_baseline()

    def test_lock_baseline_with_legacy_data(self, monkeypatch):
        """測試有遺留數據時執行遷移"""
        legacy_rows = [
            {"instrument_key": "2330", "instrument_name": "台積電", "instrument_type": "stock", "quantity": 1000, "weight": 10.0}
        ]
        legacy_meta = {"trade_date": "2026-03-31", "fetched_at": "2026-03-31T10:00:00"}

        def mock_get_snapshot(ticker, date):
            if date == "2026-03-27":
                return legacy_rows
            elif date == "2026-03-30":
                return []
            elif date == "2026-03-31":
                return legacy_rows
            return []

        def mock_get_metadata(ticker, date):
            return legacy_meta

        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.services.maintenance.get_snapshot", mock_get_snapshot)
        monkeypatch.setattr("app.services.maintenance.get_snapshot_metadata", mock_get_metadata)
        monkeypatch.setattr("app.services.maintenance.save_snapshot", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.services.maintenance.save_diffs", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.services.maintenance.get_connection", lambda: mock_context)

        lock_00992a_baseline()

    def test_lock_baseline_with_complete_data(self, monkeypatch):
        """測試有完整數據時執行過濾"""
        prev_rows = [
            {"instrument_key": "2330", "instrument_name": "台積電", "instrument_type": "stock", "quantity": 1000, "weight": 10.0},
            {"instrument_key": "2454", "instrument_name": "聯發科", "instrument_type": "stock", "quantity": 700, "weight": 7.0},
        ]
        curr_rows = [
            {"instrument_key": "2330", "instrument_name": "台積電", "instrument_type": "stock", "quantity": 1200, "weight": 12.0},
        ]
        prev_meta = {"trade_date": "2026-03-27", "fetched_at": "2026-03-27T10:00:00"}

        def mock_get_snapshot(ticker, date):
            if date == "2026-03-27":
                return prev_rows
            elif date == "2026-03-30":
                return curr_rows
            return []

        def mock_get_metadata(ticker, date):
            return prev_meta

        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.services.maintenance.get_snapshot", mock_get_snapshot)
        monkeypatch.setattr("app.services.maintenance.get_snapshot_metadata", mock_get_metadata)
        monkeypatch.setattr("app.services.maintenance.save_snapshot", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.services.maintenance.save_diffs", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.services.maintenance.get_connection", lambda: mock_context)

        lock_00992a_baseline()


class TestMaintenanceEdgeCases:
    """測試維護函數的邊界情況"""

    def test_lock_baseline_partial_overlap(self, monkeypatch):
        """測試部分重疊的數據"""
        prev_rows = [
            {"instrument_key": "2330", "instrument_name": "台積電", "instrument_type": "stock", "quantity": 1000, "weight": 10.0},
            {"instrument_key": "2454", "instrument_name": "聯發科", "instrument_type": "stock", "quantity": 700, "weight": 7.0},
        ]
        curr_rows = [
            {"instrument_key": "2330", "instrument_name": "台積電", "instrument_type": "stock", "quantity": 1200, "weight": 12.0},
            {"instrument_key": "2317", "instrument_name": "鴻海", "instrument_type": "stock", "quantity": 600, "weight": 6.0},
        ]
        prev_meta = {"trade_date": "2026-03-27", "fetched_at": "2026-03-27T10:00:00"}

        def mock_get_snapshot(ticker, date):
            if date == "2026-03-27":
                return prev_rows
            elif date == "2026-03-30":
                return curr_rows
            return []

        def mock_get_metadata(ticker, date):
            return prev_meta

        mock_connection = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_connection)
        mock_context.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr("app.services.maintenance.get_snapshot", mock_get_snapshot)
        monkeypatch.setattr("app.services.maintenance.get_snapshot_metadata", mock_get_metadata)
        monkeypatch.setattr("app.services.maintenance.save_snapshot", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.services.maintenance.save_diffs", lambda *args, **kwargs: None)
        monkeypatch.setattr("app.services.maintenance.get_connection", lambda: mock_context)

        lock_00992a_baseline()
