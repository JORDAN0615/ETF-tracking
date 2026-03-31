from app.models import Holding
from app.services.diff import build_diffs


def test_build_diffs_add_increase_decrease_remove() -> None:
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

    assert diffs["2317"].change_type == "add"
    assert diffs["2317"].quantity_delta == 600
    assert diffs["2330"].change_type == "increase"
    assert diffs["2330"].quantity_delta == 200
    assert diffs["2454"].change_type == "decrease"
    assert diffs["2454"].quantity_delta == -300
    assert diffs["2303"].change_type == "remove"
    assert diffs["2303"].curr_quantity is None
