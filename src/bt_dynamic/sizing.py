"""Position sizing applied to backtest trades after the run.

The engine always trades unit lots; sizing reweights each closed trade's
``result_pips`` by a lot derived from the trade's ``ax1`` value at entry:

- ``flat``: constant lot.
- ``proportional``: lot grows with ax1 (bet more when the trend axis is high).
- ``inverse``: lot shrinks as ax1 grows.

All methods are normalized to a mean lot of 1 across the trade set, so their
totals are comparable to the unsized run. Which cell uses which method is
injected via ``Config.lot_strategy`` — the mapping is edge and stays outside
the package, like ``regime_strategy``.
"""

from __future__ import annotations

import pandas as pd

from bt_dynamic.config import Cell, LOT_METHODS


def lot_table(trades: list[dict]) -> pd.DataFrame:
    """Per-trade lots for every method, each normalized to mean 1."""
    trades_df = pd.DataFrame(trades)
    ax1_mean = float(trades_df["ax1"].mean())
    raw = pd.DataFrame(
        {
            "flat": 1.0,
            "proportional": trades_df["ax1"] / ax1_mean,
            "inverse": ax1_mean / trades_df["ax1"].clip(lower=0.1),
        },
        index=trades_df.index,
    )
    return raw.div(raw.mean())


def apply_lot_strategy(
    trades: list[dict], lot_strategy: dict[Cell, str]
) -> list[dict]:
    """Return trades with ``lot`` and ``sized_pips`` added.

    Every regime cell present in the trades must be mapped in
    ``lot_strategy``; a missing cell is a config error, not a default.
    """
    if not trades:
        return []

    missing = sorted({t["regime"] for t in trades} - set(lot_strategy))
    if missing:
        raise ValueError(f"lot_strategy missing cell(s): {missing}")

    lots = lot_table(trades)
    sized = []
    for idx, trade in enumerate(trades):
        lot = float(lots.at[idx, lot_strategy[trade["regime"]]])
        sized.append(
            {**trade, "lot": lot, "sized_pips": trade["result_pips"] * lot}
        )
    return sized
