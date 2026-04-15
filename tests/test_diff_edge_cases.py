from __future__ import annotations

from decimal import Decimal

from app.models import Holding, HoldingDiff
from app.services.diff import build_diffs, _as_float, _top_holdings, _index_holdings


class TestAsFloat:
    """測試 _as_float 輔助函數"""

    def test_as_float_none(self):
        """測試 None 值"""
        assert _as_float(None) == 0.0

    def test_as_float_decimal(self):
        """測試 Decimal 值"""
        assert _as_float(Decimal("10.5")) == 10.5

    def test_as_float_int(self):
        """測試整數"""
        assert _as_float(100) == 100.0

    def test_as_float_float(self):
        """測試浮點數"""
        assert _as_float(10.5) == 10.5


class TestTopHoldings:
    """測試 _top_holdings 函數"""

    def test_top_holdings_basic(self):
        """測試基本排序"""
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
            Holding("2454", "聯發科", "stock", 700, 7.0),
            Holding("2303", "聯電", "stock", 500, 5.0),
        ]
        result = _top_holdings(holdings, limit=2)
        assert len(result) == 2
        assert result[0].instrument_key == "2330"
        assert result[1].instrument_key == "2454"

    def test_top_holdings_with_none_weight(self):
        """測試權重為 None 的排序"""
        holdings = [
            Holding("2330", "台積電", "stock", 1000, None),
            Holding("2454", "聯發科", "stock", 700, 7.0),
        ]
        result = _top_holdings(holdings)
        # None weight should be ranked lower
        assert result[0].instrument_key == "2454"

    def test_top_holdings_empty(self):
        """測試空列表"""
        result = _top_holdings([])
        assert result == []

    def test_top_holdings_less_than_limit(self):
        """測試持股少於限制數量"""
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
        ]
        result = _top_holdings(holdings, limit=10)
        assert len(result) == 1

    def test_top_holdings_same_weight_sort_by_quantity(self):
        """測試相同權重時按數量排序"""
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
            Holding("2454", "聯發科", "stock", 2000, 10.0),
        ]
        result = _top_holdings(holdings)
        assert result[0].instrument_key == "2454"

    def test_top_holdings_same_weight_and_quantity_sort_by_key(self):
        """測試相同權重和數量時按代號排序"""
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
            Holding("2454", "聯發科", "stock", 1000, 10.0),
        ]
        result = _top_holdings(holdings)
        # Should be sorted by instrument_key
        assert result[0].instrument_key == "2330"


class TestIndexHoldings:
    """測試 _index_holdings 函數"""

    def test_index_holdings_basic(self):
        """測試基本索引"""
        holdings = [
            Holding("2330", "台積電", "stock", 1000, 10.0),
            Holding("2454", "聯發科", "stock", 700, 7.0),
        ]
        result = _index_holdings(holdings)
        assert "2330" in result
        assert "2454" in result
        assert result["2330"].instrument_name == "台積電"

    def test_index_holdings_empty(self):
        """測試空列表"""
        result = _index_holdings([])
        assert result == {}


class TestBuildDiffsEdgeCases:
    """測試 build_diffs 的邊界情況"""

    def test_build_diffs_empty_previous(self):
        """測試空 previous"""
        current = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        diffs = build_diffs([], current)
        assert len(diffs) == 1
        assert diffs[0].change_type == "enter_top10"

    def test_build_diffs_empty_current(self):
        """測試空 current"""
        previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        diffs = build_diffs(previous, [])
        assert len(diffs) == 1
        assert diffs[0].change_type == "exit_top10"

    def test_build_diffs_both_empty(self):
        """測試兩者皆空"""
        diffs = build_diffs([], [])
        assert diffs == []

    def test_build_diffs_no_changes(self):
        """測試沒有變化"""
        holdings = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        diffs = build_diffs(holdings, holdings)
        assert diffs == []

    def test_build_diffs_weight_only_change(self):
        """測試只有權重變化"""
        previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        current = [Holding("2330", "台積電", "stock", 1000, 12.0)]
        diffs = build_diffs(previous, current)
        # No diff when quantity is the same
        assert diffs == []

    def test_build_diffs_negative_delta(self):
        """測試負數 delta"""
        previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        current = [Holding("2330", "台積電", "stock", 500, 5.0)]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].change_type == "decrease"
        assert diffs[0].quantity_delta == -500

    def test_build_diffs_zero_quantity(self):
        """測試零數量"""
        previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        current = [Holding("2330", "台積電", "stock", 0, 0.0)]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].change_type == "decrease"
        assert diffs[0].quantity_delta == -1000

    def test_build_diffs_decimal_values(self):
        """測試 Decimal 值"""
        previous = [Holding("2330", "台積電", "stock", Decimal("1000"), Decimal("10.0"))]
        current = [Holding("2330", "台積電", "stock", Decimal("1200"), Decimal("12.0"))]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].quantity_delta == 200.0

    def test_build_diffs_weight_delta_none(self):
        """測試權重 delta 為 None"""
        previous = [Holding("2330", "台積電", "stock", 1000, None)]
        current = [Holding("2330", "台積電", "stock", 1200, 12.0)]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].weight_delta is None

    def test_build_diffs_both_weights_none(self):
        """測試兩者權重皆為 None"""
        previous = [Holding("2330", "台積電", "stock", 1000, None)]
        current = [Holding("2330", "台積電", "stock", 1200, None)]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].weight_delta is None

    def test_build_diffs_mixed_decimal_float(self):
        """測試混合 Decimal 和 float"""
        previous = [Holding("2330", "台積電", "stock", Decimal("1000"), 10.0)]
        current = [Holding("2330", "台積電", "stock", 1200.0, Decimal("12.0"))]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].quantity_delta == 200.0
        assert diffs[0].weight_delta == 2.0

    def test_build_diffs_large_numbers(self):
        """測試大數字"""
        previous = [Holding("2330", "台積電", "stock", 1000000, 50.0)]
        current = [Holding("2330", "台積電", "stock", 2000000, 60.0)]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].quantity_delta == 1000000

    def test_build_diffs_small_changes(self):
        """測試微小變化"""
        previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        current = [Holding("2330", "台積電", "stock", 1001, 10.01)]
        diffs = build_diffs(previous, current)
        assert len(diffs) == 1
        assert diffs[0].quantity_delta == 1

    def test_build_diffs_instrument_name_from_current(self):
        """測試 instrument_name 來自 current"""
        previous = [Holding("2330", "舊名稱", "stock", 1000, 10.0)]
        current = [Holding("2330", "新名稱", "stock", 1200, 12.0)]
        diffs = build_diffs(previous, current)
        assert diffs[0].instrument_name == "新名稱"

    def test_build_diffs_instrument_name_from_previous_on_exit(self):
        """測試 exit_top10 時 instrument_name 來自 previous"""
        previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
        current = []
        diffs = build_diffs(previous, current)
        assert diffs[0].instrument_name == "台積電"
