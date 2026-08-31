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
from bt_dynamic.engine import dispersion, run_day, summarize_dict
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
    cells: dict[Cell, str] | None = None,
) -> dict[Cell, dict]:
    """Backtest cells in isolation, one run per cell.

    By default this covers only the cells ``config.regime_strategy`` acts on,
    which for a single-cell config is a single row — not a view of the 9-cell
    grid. Pass ``cells`` (e.g. ``{c: "follow" for c in ALL_CELLS}``) to also
    score the cells the config leaves flat, which is the only way to ask
    whether a cell was left out for a reason.

    The per-cell sums do not add up to the all-cells-together summary: in
    single-position mode, cells compete for the same position slot, so
    isolating one cell frees it from that competition. This non-additivity is
    expected, not a bug — observing both views separately is the point.
    """
    mapping = cells if cells is not None else {
        cell: mode for cell, mode in config.regime_strategy.items() if mode is not None
    }
    results: dict[Cell, dict] = {}
    for cell, mode in mapping.items():
        solo_config = replace(config, regime_strategy={cell: mode})
        trades = run_period(
            bars, dates, solo_config, indicators=indicators, multi_position=multi_position
        )
        results[cell] = summarize_dict(trades)
    return results


def _daily_pips(trades: list[dict], dates: list[date]) -> pd.Series:
    """Per-day sum of ``result_pips``, reindexed to ``dates`` with 0.0 for days without a trade.

    Grouped by ``entry_time``'s date, not ``exit_time``: a day's trading
    window sits entirely inside that calendar day (``engine.run_day`` only
    opens positions inside the target day and force-closes anything still
    open at EOD), so the entry date already identifies the day even for a
    force-closed position.
    """
    daily = pd.Series(0.0, index=pd.Index(dates))
    if not trades:
        return daily
    df = pd.DataFrame(trades)
    entry_dates = pd.DatetimeIndex(df["entry_time"]).date
    by_day = df.groupby(entry_dates)["result_pips"].sum()
    return by_day.reindex(dates, fill_value=0.0)


def _paired_diff_stats(
    baseline_trades: list[dict], candidate_trades: list[dict], dates: list[date]
) -> dict:
    """Day-paired diff (candidate minus baseline) from already-run trades.

    The index for pairing is ``dates`` itself, not "days either side
    traded": a day where only one side entered still counts, as 0.0 for
    the side that stayed flat, otherwise conditioning on "both sides
    traded" would bias the estimate. The std/stderr/t/CI cluster is
    ``engine.dispersion`` applied to the daily diff series, so it inherits
    its rules verbatim (fewer than two days, or a zero-variance diff,
    leaves those fields ``None``) instead of re-implementing them.
    """
    diff = _daily_pips(candidate_trades, dates) - _daily_pips(baseline_trades, dates)
    return {
        "days": len(dates),
        "mean_diff_pips": round(float(diff.mean()), 3),
        **dispersion(diff),
    }


def paired_diff(
    bars: pd.DataFrame,
    dates: list[date],
    baseline: Config,
    candidate: Config,
    indicators: IndicatorSet = DEFAULT_INDICATORS,
    multi_position: bool = False,
) -> dict:
    """Run two configs over the same dates and score their day-paired diff.

    Evaluating ``baseline`` and ``candidate`` independently (as
    ``param_sweep`` does for its per-candidate ``summary``) throws away the
    fact that both runs sit on the same days and share the same market
    noise. Pairing by day and looking at the diff directly cancels that
    shared noise, so the resulting interval is narrower than one computed
    from the two independent summaries — it will not match a value derived
    from their independent ``std``/``stderr`` (that would assume
    uncorrelated runs). This is the whole reason the function exists rather
    than just subtracting two ``summarize_dict`` totals.

    Pairing is by day, not by trade: a config change shifts exit times and,
    in single-position mode, which later entries are even reachable, so the
    two sides' trades don't line up 1:1. Days are the only index both runs
    share.

    Returns ``{"days", "mean_diff_pips", "std_pips", "stderr_pips",
    "t_stat", "ci95_low", "ci95_high"}`` — the last five straight from
    ``engine.dispersion``. Equal configs make every day's diff 0.0, so
    ``mean_diff_pips`` is 0.0 and the zero-variance rule leaves the rest
    ``None``.
    """
    baseline_trades = run_period(
        bars, dates, baseline, indicators=indicators, multi_position=multi_position
    )
    candidate_trades = run_period(
        bars, dates, candidate, indicators=indicators, multi_position=multi_position
    )
    return _paired_diff_stats(baseline_trades, candidate_trades, dates)


def param_sweep(
    bars: pd.DataFrame,
    dates: list[date],
    config: Config,
    overrides: list[dict],
    indicators: IndicatorSet = DEFAULT_INDICATORS,
    multi_position: bool = False,
) -> list[dict]:
    """Evaluate ``config`` plus each of ``overrides``, ranked by t-statistic.

    Each ``overrides`` item is a ``dict`` of ``Config.override(**kwargs)``
    keyword arguments (concrete parameter names are the caller's concern,
    not this module's). The unmodified ``config`` is always included as an
    empty-override candidate, so the grid shows where the current values
    rank.

    Ranking is by ``t_stat``, not by total pips: the candidate with the
    largest sum is often just the one that took the most trades, and this
    module exists to stop that number from deciding anything. Each result
    also carries its ``trades``, so the caller can break a candidate down by
    year or by train/test without re-running it, plus ``diff_vs_base``: the
    day-paired diff (see :func:`paired_diff`) against the empty-override
    candidate, computed from the ``trades`` already collected here rather
    than re-running the backtest. The base candidate's own ``diff_vs_base``
    is therefore all zeros.
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
        results.append(
            {"overrides": override, "summary": summarize_dict(trades), "trades": trades}
        )

    base_trades = results[0]["trades"]  # candidates[0] is always the empty override
    for result in results:
        result["diff_vs_base"] = _paired_diff_stats(base_trades, result["trades"], dates)

    results.sort(key=_rank_key, reverse=True)
    return results


def _rank_key(result: dict) -> tuple[int, float]:
    """Sort key for :func:`param_sweep`: t-statistic, undefined ones last."""
    t_stat = result["summary"].get("t_stat")
    return (0, 0.0) if t_stat is None else (1, t_stat)
