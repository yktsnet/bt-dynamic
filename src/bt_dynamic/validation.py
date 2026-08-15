"""Evaluation layer on top of ``engine``: multi-day runs, train/test splits,
per-cell contribution, and parameter grid sweeps.

This exists because "does it net positive over the whole period" hides
overfitting: a cell that looks good on a handful of non-contiguous seasonal
days can be negative once run over a contiguous multi-year span. The
functions here make that kind of check a reusable API instead of a
throwaway script.

Sits above ``regime``/``engine``/``config`` and may import them; nothing in
those modules imports this one back.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from bt_dynamic.config import Cell, Config
from bt_dynamic.engine import run_day, summarize_dict
from bt_dynamic.indicators import DEFAULT_INDICATORS, IndicatorSet


def run_period(
    bars: pd.DataFrame,
    dates: list[date],
    config: Config,
    indicators: IndicatorSet = DEFAULT_INDICATORS,
    multi_position: bool = False,
) -> list[dict]:
    """Run consecutive days and concatenate the trades in time order.

    ``bars`` must already span the whole period as one DataFrame (a
    per-year split would lose the previous day's warm-up across year
    boundaries). Days with no data in ``bars`` are silently skipped, since
    ``run_day`` already returns ``[]`` for them rather than raising.
    """
    trades: list[dict] = []
    for target in dates:
        trades.extend(
            run_day(
                bars,
                target.isoformat(),
                config,
                indicators=indicators,
                multi_position=multi_position,
            )
        )
    return trades


def split_train_test(dates: list[date], ratio: float) -> tuple[list[date], list[date]]:
    """Split a chronologically ordered date list into leading train / trailing test.

    No shuffling or random sampling: the split relies on the input staying
    in time order. ``ratio`` is the train share; a ratio that would leave
    either side empty is rejected.
    """
    cut = round(len(dates) * ratio)
    if not 0 < ratio < 1 or cut <= 0 or cut >= len(dates):
        raise ValueError(
            f"ratio {ratio!r} collapses to an empty split for {len(dates)} dates"
        )
    return list(dates[:cut]), list(dates[cut:])


def cell_breakdown(
    bars: pd.DataFrame,
    dates: list[date],
    config: Config,
    indicators: IndicatorSet = DEFAULT_INDICATORS,
    multi_position: bool = False,
) -> dict[Cell, dict]:
    """Backtest each active cell of ``config.regime_strategy`` in isolation.

    Returns ``{cell: summarize_dict(...)}`` for every cell whose mode is not
    ``None``. The per-cell sums do not add up to the all-cells-together
    summary: in single-position mode, cells compete for the same position
    slot, so isolating one cell frees it from that competition. This
    non-additivity is expected, not a bug — observing both views separately
    is the point of this function.
    """
    results: dict[Cell, dict] = {}
    for cell, mode in config.regime_strategy.items():
        if mode is None:
            continue
        solo_config = replace(config, regime_strategy={cell: mode})
        trades = run_period(
            bars, dates, solo_config, indicators=indicators, multi_position=multi_position
        )
        results[cell] = summarize_dict(trades)
    return results


def param_sweep(
    bars: pd.DataFrame,
    dates: list[date],
    config: Config,
    overrides: list[dict],
    indicators: IndicatorSet = DEFAULT_INDICATORS,
    multi_position: bool = False,
) -> list[dict]:
    """Evaluate ``config`` plus each of ``overrides``, ranked by total pips.

    Each ``overrides`` item is a ``dict`` of ``Config.override(**kwargs)``
    keyword arguments (concrete parameter names are the caller's concern,
    not this module's). The unmodified ``config`` is always included as an
    empty-override candidate, so the grid shows where the current values
    rank. Results are sorted by ``summary["total_pips"]`` descending (trade-
    less candidates, which have no ``total_pips`` key, sort as 0.0).
    """
    candidates = [{}, *overrides]
    results = []
    for override in candidates:
        candidate_config = config.override(**override) if override else config
        trades = run_period(
            bars,
            dates,
            candidate_config,
            indicators=indicators,
            multi_position=multi_position,
        )
        results.append({"overrides": override, "summary": summarize_dict(trades)})
    results.sort(key=lambda r: r["summary"].get("total_pips", 0.0), reverse=True)
    return results
