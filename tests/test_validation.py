from datetime import date

import numpy as np
import pandas as pd
import pytest

from bt_dynamic.config import Config
from bt_dynamic.validation import cell_breakdown, param_sweep, run_period, split_train_test


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


def test_param_sweep_includes_base_config_and_sorts_descending():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    overrides = [{"tp_pips": 5.0}, {"tp_pips": 40.0}, {"tp_pips": 1.0}]

    results = param_sweep(df, TRADE_DATES, config, overrides)

    assert len(results) == len(overrides) + 1
    assert any(r["overrides"] == {} for r in results)

    totals = [r["summary"].get("total_pips", 0.0) for r in results]
    assert totals == sorted(totals, reverse=True)


def test_functions_do_not_mutate_config_or_bars():
    df = _make_mixed_trend_bars(days=6)
    config = _permissive_config()
    strategy_before = dict(config.regime_strategy)
    df_before = df.copy()

    run_period(df, TRADE_DATES, config)
    cell_breakdown(df, TRADE_DATES, config)
    param_sweep(df, TRADE_DATES, config, [{"tp_pips": 5.0}])
    split_train_test(TRADE_DATES, ratio=0.5)

    assert config.regime_strategy == strategy_before
    pd.testing.assert_frame_equal(df, df_before)
