from decimal import Decimal

from app.models import Holding
from app.services.diff import build_diffs


def test_build_diffs_enter_increase_decrease_exit() -> None:
    previous = [
        Holding("2330", "台積電", "stock", 1000, 10.0),
        Holding("2454", "聯發科", "stock", 700, 7.0),
        Holding("2303", "聯電", "stock", 500, 4.0),
    ]
    current = [
        Holding("2330", "台積電", "stock", 1200, 12.0),
        Holding("2454", "聯發科", "stock", 400, 5.5),
        Holding("2317", "鴻海", "stock", 600, 6.0),
    ]

    diffs = {item.instrument_key: item for item in build_diffs(previous, current)}

    assert diffs["2317"].change_type == "enter_top10"
    assert diffs["2317"].quantity_delta == 600
    assert diffs["2330"].change_type == "increase"
    assert diffs["2330"].quantity_delta == 200
    assert diffs["2454"].change_type == "decrease"
    assert diffs["2454"].quantity_delta == -300
    assert diffs["2303"].change_type == "exit_top10"
    assert diffs["2303"].curr_quantity is None


def test_build_diffs_only_uses_top10_from_each_day() -> None:
    previous = [
        Holding(f"{1000 + i}", f"Prev{i}", "stock", 1000 + i, float(100 - i))
        for i in range(12)
    ]
    current = [
        Holding(f"{1000 + i}", f"Curr{i}", "stock", 1000 + i + (10 if i < 10 else 0), float(100 - i))
        for i in range(12)
    ]
    # Force one top10 exit and one top10 enter by lowering/raising weights.
    previous[9] = Holding("1909", "PrevOut", "stock", 2000, 91.0)
    previous[10] = Holding("1910", "PrevLow", "stock", 1500, 90.0)
    current[9] = Holding("1909", "PrevOut", "stock", 2000, 89.0)
    current[10] = Holding("1910", "PrevLow", "stock", 1500, 95.0)

    diffs = build_diffs(previous, current)
    keys = {item.instrument_key for item in diffs}

    assert "1910" in keys
    assert "1909" in keys
    # Item outside both top10 sets should not appear.
    assert "1011" not in keys


def test_build_diffs_accepts_decimal_and_float_mixed_numbers() -> None:
    previous = [Holding("2330", "台積電", "stock", Decimal("1000"), Decimal("10.0"))]
    current = [Holding("2330", "台積電", "stock", 1200.0, 10.5)]

    diffs = build_diffs(previous, current)

    assert len(diffs) == 1
    assert diffs[0].change_type == "increase"
    assert diffs[0].quantity_delta == 200.0
