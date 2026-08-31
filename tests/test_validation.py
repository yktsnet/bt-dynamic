from datetime import date

import numpy as np
import pandas as pd
import pytest

from bt_dynamic.config import Config
from bt_dynamic.engine import dispersion
from bt_dynamic.regime import ALL_CELLS
from bt_dynamic.validation import (
    cell_breakdown,
    paired_diff,
    param_sweep,
    run_period,
    split_train_test,
)


def _make_mixed_trend_bars(days: int = 6, bars_per_day: int = 120):
    """Alternating weak/strong/reversing trend days so different decision
    points land in different regime cells (needed for cell_breakdown to
    actually exercise more than one cell)."""
    rng = np.random.default_rng(11)
    rows = []
    price = 150.0
    start = pd.Timestamp("2025-01-06")  # Monday
    drifts = [0.0005, 0.03, -0.03, 0.0005, 0.03, -0.01]
    for day in range(days):
        drift = drifts[day % len(drifts)]
        day_start = start + pd.Timedelta(days=day)
        for i in range(bars_per_day):
            open_ = price
            close = open_ + drift + rng.normal(0, 0.01)
            high = max(open_, close) + abs(rng.normal(0, 0.005))
            low = min(open_, close) - abs(rng.normal(0, 0.005))
            price = close
            rows.append(
                {
                    "time": day_start + pd.Timedelta(minutes=5 * i),
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            )
    return pd.DataFrame(rows).set_index("time")


def _permissive_config(**param_overrides) -> Config:
    strategy = {f"{a},{b}": "follow" for a in range(3) for b in range(3)}
    return Config.from_dict(
        {
            "parameters": {"direction_band": 2.0, **param_overrides},
            "regime_strategy": strategy,
        }
    )


# business days only, skipping the warm-up-only first day (2025-01-06)
TRADE_DATES = [date(2025, 1, 7), date(2025, 1, 8), date(2025, 1, 9), date(2025, 1, 10)]


def test_run_period_concatenates_in_order_and_skips_missing_days():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()

    missing = date(2099, 1, 1)  # no data for this day at all
    trades = run_period(df, [*TRADE_DATES, missing], config)

    assert trades, "a trending mixed dataset with all-follow must trade"
    times = [t["entry_time"] for t in trades]
    assert times == sorted(times)

    # matches calling run_day per day and concatenating
    expected = []
    for d in TRADE_DATES:
        expected.extend(run_period(df, [d], config))
    assert len(trades) == len(expected)


def test_split_train_test_preserves_chronological_order():
    dates = [date(2025, 1, d) for d in range(1, 11)]
    train, test = split_train_test(dates, ratio=0.7)

    assert train == dates[:7]
    assert test == dates[7:]
    assert train + test == dates


@pytest.mark.parametrize("ratio", [0.0, 1.0, -0.1, 1.5])
def test_split_train_test_rejects_degenerate_ratio(ratio):
    dates = [date(2025, 1, d) for d in range(1, 11)]
    with pytest.raises(ValueError):
        split_train_test(dates, ratio)


def test_split_train_test_rejects_ratio_that_empties_small_input():
    dates = [date(2025, 1, 1), date(2025, 1, 2)]
    with pytest.raises(ValueError):
        split_train_test(dates, ratio=0.01)


def test_cell_breakdown_is_not_additive_with_combined_run():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()

    breakdown = cell_breakdown(df, TRADE_DATES, config)
    assert breakdown, "mixed-trend data under an all-follow config must hit multiple cells"

    solo_total = sum(
        summary.get("total_pips", 0.0) for summary in breakdown.values()
    )
    solo_trade_count = sum(summary.get("trades", 0) for summary in breakdown.values())

    combined = run_period(df, TRADE_DATES, config)
    combined_total = sum(t["result_pips"] for t in combined)
    combined_trade_count = len(combined)

    # single-position mode: cells compete for the position slot, so running
    # each cell alone changes both the trade count and the total pips.
    assert solo_trade_count != combined_trade_count
    assert solo_total != pytest.approx(combined_total)


def test_cell_breakdown_only_covers_active_cells():
    df = _make_mixed_trend_bars(days=6)
    config = Config.from_dict(
        {
            "parameters": {"direction_band": 2.0},
            "regime_strategy": {"0,0": "follow", "1,1": None},
        }
    )
    breakdown = cell_breakdown(df, TRADE_DATES, config)
    assert set(breakdown) == {(0, 0)}


def test_cell_breakdown_can_score_cells_the_config_leaves_flat():
    df = _make_mixed_trend_bars(days=6)
    config = Config.from_dict(
        {
            "parameters": {"direction_band": 2.0},
            "regime_strategy": {"0,0": "follow"},
        }
    )

    scanned = cell_breakdown(
        df, TRADE_DATES, config, cells={cell: "follow" for cell in ALL_CELLS}
    )

    assert set(scanned) == set(ALL_CELLS)
    # the configured cell is scored identically either way
    assert scanned[(0, 0)] == cell_breakdown(df, TRADE_DATES, config)[(0, 0)]
    # and at least one unconfigured cell actually produced trades to compare
    assert any(
        cell != (0, 0) and summary.get("trades") for cell, summary in scanned.items()
    )


def test_param_sweep_includes_base_config_and_ranks_by_t_stat():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    overrides = [{"tp_pips": 5.0}, {"tp_pips": 40.0}, {"tp_pips": 1.0}]

    results = param_sweep(df, TRADE_DATES, config, overrides)

    assert len(results) == len(overrides) + 1
    assert any(r["overrides"] == {} for r in results)

    # ranked by t_stat, with candidates too small to have one pushed to the end
    ranked = [r["summary"].get("t_stat") for r in results]
    scored = [t for t in ranked if t is not None]
    assert scored == sorted(scored, reverse=True)
    assert ranked[: len(scored)] == scored


def test_param_sweep_carries_trades_for_caller_side_breakdowns():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()

    results = param_sweep(df, TRADE_DATES, config, [{"tp_pips": 5.0}])

    for result in results:
        assert len(result["trades"]) == result["summary"].get("trades", 0)
        # enough to slice by period without re-running the sweep
        assert all("entry_time" in t for t in result["trades"])


def test_param_sweep_does_not_rank_by_total_pips():
    """A sum rewards whichever candidate simply traded the most.

    A tight TP fires far more often than a distant one, so the two rankings
    come apart; if they ever stopped doing so this test would be vacuous.
    """
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    overrides = [{"tp_pips": 2.0}, {"tp_pips": 40.0}, {"sl_pips": 2.0}]

    results = param_sweep(df, TRADE_DATES, config, overrides)
    totals = [r["summary"].get("total_pips", 0.0) for r in results]

    assert totals != sorted(totals, reverse=True)


PAIRED_DIFF_KEYS = {
    "days", "mean_diff_pips", "std_pips", "stderr_pips", "t_stat", "ci95_low", "ci95_high",
}


def test_paired_diff_returns_expected_keys_and_day_count():
    df = _make_mixed_trend_bars(days=6)
    baseline = _permissive_config()
    candidate = baseline.override(tp_pips=5.0)

    result = paired_diff(df, TRADE_DATES, baseline, candidate)

    assert set(result) == PAIRED_DIFF_KEYS
    assert result["days"] == len(TRADE_DATES)


def test_paired_diff_is_zero_for_identical_configs():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()

    result = paired_diff(df, TRADE_DATES, config, config)

    assert result["mean_diff_pips"] == 0.0
    assert result["std_pips"] == 0.0
    assert result["stderr_pips"] == 0.0
    assert result["t_stat"] is None
    assert result["ci95_low"] is None
    assert result["ci95_high"] is None


def _manual_daily_diff(df, baseline, candidate) -> list[float]:
    """Reference implementation: per-day (candidate - baseline) pips, 0.0 when a
    side takes no trade that day. Computed independently of ``validation.py``
    so it can serve as a check on the pairing/zero-fill contract."""
    diffs = []
    for d in TRADE_DATES:
        base_trades = run_period(df, [d], baseline)
        cand_trades = run_period(df, [d], candidate)
        base_sum = sum(t["result_pips"] for t in base_trades)
        cand_sum = sum(t["result_pips"] for t in cand_trades)
        diffs.append(cand_sum - base_sum)
    return diffs


def test_paired_diff_pairs_by_day_and_fills_untraded_days_with_zero():
    df = _make_mixed_trend_bars(days=6)
    # only one cell active: some days plausibly take zero trades for this side
    sparse = Config.from_dict(
        {
            "parameters": {"direction_band": 2.0},
            "regime_strategy": {"0,0": "follow"},
        }
    )
    permissive = _permissive_config()

    sparse_daily_counts = [
        len(run_period(df, [d], sparse)) for d in TRADE_DATES
    ]
    assert any(count == 0 for count in sparse_daily_counts), (
        "test needs at least one day where the sparse config stays flat"
    )
    assert all(
        len(run_period(df, [d], permissive)) > 0 for d in TRADE_DATES
    ), "test needs the permissive config to trade every day, to exercise the one-sided fill"

    expected_diffs = _manual_daily_diff(df, sparse, permissive)
    result = paired_diff(df, TRADE_DATES, sparse, permissive)

    assert result["mean_diff_pips"] == pytest.approx(
        sum(expected_diffs) / len(expected_diffs), abs=1e-3
    )


def test_paired_diff_does_not_match_naive_independent_combination():
    """The paired stderr must differ from one synthesized by treating the two
    configs' daily series as independent (i.e. summing variances) — matching
    independently would mean the pairing bought nothing."""
    df = _make_mixed_trend_bars(days=6)
    baseline = _permissive_config()
    candidate = baseline.override(tp_pips=5.0)

    baseline_daily = pd.Series(
        [sum(t["result_pips"] for t in run_period(df, [d], baseline)) for d in TRADE_DATES]
    )
    candidate_daily = pd.Series(
        [sum(t["result_pips"] for t in run_period(df, [d], candidate)) for d in TRADE_DATES]
    )
    base_spread = dispersion(baseline_daily)
    cand_spread = dispersion(candidate_daily)
    naive_stderr = (base_spread["stderr_pips"] ** 2 + cand_spread["stderr_pips"] ** 2) ** 0.5

    result = paired_diff(df, TRADE_DATES, baseline, candidate)

    assert result["stderr_pips"] != pytest.approx(naive_stderr, rel=1e-6)


def test_param_sweep_carries_diff_vs_base_computed_from_existing_trades():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    overrides = [{"tp_pips": 5.0}, {"tp_pips": 40.0}]

    results = param_sweep(df, TRADE_DATES, config, overrides)

    for result in results:
        assert set(result["diff_vs_base"]) == PAIRED_DIFF_KEYS

    base_result = next(r for r in results if r["overrides"] == {})
    assert base_result["diff_vs_base"]["mean_diff_pips"] == 0.0
    assert base_result["diff_vs_base"]["t_stat"] is None

    tp5_result = next(r for r in results if r["overrides"] == {"tp_pips": 5.0})
    expected = paired_diff(df, TRADE_DATES, config, config.override(tp_pips=5.0))
    assert tp5_result["diff_vs_base"] == expected


def test_param_sweep_computes_diff_without_rerunning_the_backtest(monkeypatch):
    import bt_dynamic.validation as validation_module

    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    overrides = [{"tp_pips": 5.0}, {"tp_pips": 40.0}]

    calls = []
    original_run_period = validation_module.run_period

    def counting_run_period(*args, **kwargs):
        calls.append(1)
        return original_run_period(*args, **kwargs)

    monkeypatch.setattr(validation_module, "run_period", counting_run_period)

    param_sweep(df, TRADE_DATES, config, overrides)

    # one run_period call per candidate (base + overrides); computing
    # diff_vs_base from the trades already collected must not add more
    assert len(calls) == len(overrides) + 1


def test_functions_do_not_mutate_config_or_bars():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    strategy_before = dict(config.regime_strategy)
    df_before = df.copy()

    run_period(df, TRADE_DATES, config)
    cell_breakdown(df, TRADE_DATES, config)
    param_sweep(df, TRADE_DATES, config, [{"tp_pips": 5.0}])
    paired_diff(df, TRADE_DATES, config, config.override(tp_pips=5.0))
    split_train_test(TRADE_DATES, ratio=0.5)

    assert config.regime_strategy == strategy_before
    pd.testing.assert_frame_equal(df, df_before)
