from __future__ import annotations

from typing import Iterable

from app.models import Holding, HoldingDiff


def _index_holdings(holdings: Iterable[Holding]) -> dict[str, Holding]:
    return {holding.instrument_key: holding for holding in holdings}


def build_diffs(previous: Iterable[Holding], current: Iterable[Holding]) -> list[HoldingDiff]:
    previous_map = _index_holdings(previous)
    current_map = _index_holdings(current)

    diffs: list[HoldingDiff] = []
    all_keys = sorted(set(previous_map) | set(current_map))
    for key in all_keys:
        prev_item = previous_map.get(key)
        curr_item = current_map.get(key)

        prev_quantity = prev_item.quantity if prev_item else 0.0
        curr_quantity = curr_item.quantity if curr_item else 0.0
        prev_weight = prev_item.weight if prev_item else None
        curr_weight = curr_item.weight if curr_item else None
        quantity_delta = curr_quantity - prev_quantity
        weight_delta = (
            None
            if prev_weight is None or curr_weight is None
            else curr_weight - prev_weight
        )

        if prev_item is None and curr_item is not None:
            change_type = "add"
        elif curr_item is None and prev_item is not None:
            change_type = "remove"
        elif quantity_delta > 0:
            change_type = "increase"
        elif quantity_delta < 0:
            change_type = "decrease"
        else:
            continue

        instrument_name = curr_item.instrument_name if curr_item else prev_item.instrument_name
        diffs.append(
            HoldingDiff(
                instrument_key=key,
                instrument_name=instrument_name,
                change_type=change_type,
                quantity_delta=quantity_delta,
                weight_delta=weight_delta,
                prev_quantity=prev_item.quantity if prev_item else None,
                curr_quantity=curr_item.quantity if curr_item else None,
                prev_weight=prev_weight,
                curr_weight=curr_weight,
            )
        )

    return diffs
