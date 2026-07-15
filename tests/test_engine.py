import numpy as np
import pandas as pd
import pytest

from bt_dynamic.config import Config, Params
from bt_dynamic.engine import _check_exit, calc_result_pips, resolve_entry, run_day, summarize_dict

PARAMS = Params()


def test_calc_result_pips():
    assert calc_result_pips("BUY", 150.0, 150.30, 0.01) == pytest.approx(30.0)
    assert calc_result_pips("BUY", 150.0, 149.70, 0.01) == pytest.approx(-30.0)
    assert calc_result_pips("SELL", 150.0, 149.70, 0.01) == pytest.approx(30.0)
    assert calc_result_pips("SELL", 150.0, 150.30, 0.01) == pytest.approx(-30.0)


def test_check_exit():
    pos = {"direction": "BUY", "entry_price": 150.0, "sl": 149.90, "tp": 150.30}

    assert _check_exit(pos, {"low": 149.95, "high": 150.25}) == (None, None)
    assert _check_exit(pos, {"low": 149.85, "high": 150.10}) == ("SL", 149.90)
    assert _check_exit(pos, {"low": 150.05, "high": 150.35}) == ("TP", 150.30)


def test_resolve_entry_follow_and_flip():
    follow = resolve_entry(150.0, "follow", "BUY", PARAMS)
    assert follow["direction"] == "BUY"
    assert follow["tp"] == pytest.approx(150.0 + PARAMS.tp_pips * PARAMS.pip)
    assert follow["sl"] == pytest.approx(150.0 - PARAMS.sl_pips * PARAMS.pip)

    flip = resolve_entry(150.0, "flip", "BUY", PARAMS)
    assert flip["direction"] == "SELL"
    assert flip["tp"] == pytest.approx(150.0 - PARAMS.tp_pips * PARAMS.pip)

    assert resolve_entry(150.0, None, "BUY", PARAMS) is None
    assert resolve_entry(150.0, "follow", None, PARAMS) is None


def _make_bars(start: str, days: int, bars_per_day: int = 120, seed: int = 7):
    """Synthetic uptrending m5 bars: strong trend, so ax1 lands high."""
    rng = np.random.default_rng(seed)
    rows = []
    price = 150.0
    for day in range(days):
        day_start = pd.Timestamp(start) + pd.Timedelta(days=day)
        for i in range(bars_per_day):
            open_ = price
            close = open_ + 0.01 + rng.normal(0, 0.005)
            high = max(open_, close) + abs(rng.normal(0, 0.003))
            low = min(open_, close) - abs(rng.normal(0, 0.003))
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


def _permissive_config() -> Config:
    # every cell trades "follow" so the synthetic trend must produce entries
    strategy = {f"{a},{b}": "follow" for a in range(3) for b in range(3)}
    return Config.from_dict(
        {"parameters": {"direction_band": 2.0}, "regime_strategy": strategy}
    )


def test_run_day_produces_trades():
    df = _make_bars("2025-01-06", days=2)  # Mon warmup, Tue trade
    config = _permissive_config()

    trades = run_day(df, "2025-01-07", config)

    assert trades, "an uptrend with an all-follow mapping must trade"
    for t in trades:
        assert t["exit"] in {"TP", "SL", "EOD"}
        assert t["direction"] in {"BUY", "SELL"}
        assert t["exit_time"] > t["entry_time"]
    # single-position mode: no overlapping trades
    for prev, nxt in zip(trades, trades[1:]):
        assert nxt["entry_time"] >= prev["exit_time"]
    # TP exits net exactly tp_pips minus commission
    tp_trades = [t for t in trades if t["exit"] == "TP"]
    for t in tp_trades:
        expected = config.params.tp_pips - config.params.commission_pips
        assert t["result_pips"] == pytest.approx(expected)


def test_run_day_unlisted_cell_stays_flat():
    df = _make_bars("2025-01-06", days=2)
    config = Config.from_dict({"parameters": {}, "regime_strategy": {}})

    assert run_day(df, "2025-01-07", config) == []


def test_run_day_insufficient_data():
    df = _make_bars("2025-01-06", days=2, bars_per_day=4)
    assert run_day(df, "2025-01-07", _permissive_config()) == []


def test_debug_day_records():
    from bt_dynamic.engine import debug_day

    df = _make_bars("2025-01-06", days=2)
    config = _permissive_config()

    records = debug_day(df, "2025-01-07", config)

    assert records, "decision points must be reported"
    for r in records:
        assert r["action"].startswith(("ENTRY", "skip("))
    entered = [r for r in records if r["action"].startswith("ENTRY")]
    assert entered, "an all-follow mapping on a trend must show entries"
    for r in entered:
        assert r["cell_mode"] == "follow"
        assert r["action"] == f"ENTRY {r['direction']}"  # follow keeps the bias
        assert {"ax1", "vol_ratio", "direction_val", "ax1_class", "ax2_class"} <= set(r)


def test_debug_day_flip_shows_actual_direction():
    from bt_dynamic.engine import debug_day

    df = _make_bars("2025-01-06", days=2)
    strategy = {f"{a},{b}": "flip" for a in range(3) for b in range(3)}
    config = Config.from_dict(
        {"parameters": {"direction_band": 2.0}, "regime_strategy": strategy}
    )

    entered = [
        r for r in debug_day(df, "2025-01-07", config) if r["action"].startswith("ENTRY")
    ]
    assert entered
    for r in entered:
        assert r["action"] != f"ENTRY {r['direction']}"  # flip inverts the bias


def test_run_day_dynamic_thresholds():
    # enough lookback days for percentile thresholds to kick in
    df = _make_bars("2025-01-06", days=5)
    config = _permissive_config()

    trades = run_day(df, "2025-01-10", config, use_dynamic=True, lookback_days=3)
    assert isinstance(trades, list)  # smoke: runs without error


def _make_mixed_trend_bars(bars_per_day: int = 120):
    """Alternating weak/strong trend days so ax1 (trend strength) actually varies,
    unlike a single monotonic trend where it saturates and stays flat."""
    rng = np.random.default_rng(3)
    rows = []
    price = 150.0
    start = pd.Timestamp("2025-01-06")
    drifts = [0.0005, 0.03, 0.0005, 0.03, 0.01]  # last day is the trade day
    for day, drift in enumerate(drifts):
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


def test_run_day_dynamic_thresholds_differ_from_static():
    # dynamic thresholds must actually be derived from the data distribution,
    # not merely run without error alongside the static config values.
    df = _make_mixed_trend_bars()
    config = _permissive_config()

    static_trades = run_day(df, "2025-01-10", config)
    dynamic_trades = run_day(df, "2025-01-10", config, use_dynamic=True, lookback_days=3)

    assert static_trades and dynamic_trades
    static_classes = {t["regime"][0] for t in static_trades}
    dynamic_classes = {t["regime"][0] for t in dynamic_trades}
    assert static_classes != dynamic_classes


def test_summarize_dict_empty():
    assert summarize_dict([]) == {"trades": 0}


def test_summarize_dict_aggregates():
    trades = [
        {"exit": "TP", "cell_mode": "follow", "regime": (0, 0), "result_pips": 10.0},
        {"exit": "SL", "cell_mode": "follow", "regime": (0, 0), "result_pips": -5.0},
        {"exit": "TP", "cell_mode": "flip", "regime": (1, 1), "result_pips": 20.0},
    ]

    summary = summarize_dict(trades)

    assert summary["trades"] == 3
    assert summary["wins"] == 2
    assert summary["losses"] == 1
    assert summary["win_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert summary["total_pips"] == pytest.approx(25.0)
    assert summary["avg_pips"] == pytest.approx(25.0 / 3, rel=1e-3)
    assert summary["best_pips"] == pytest.approx(20.0)
    assert summary["worst_pips"] == pytest.approx(-5.0)
    assert summary["by_exit"]["TP"]["count"] == 2
    assert summary["by_exit"]["SL"]["count"] == 1
    assert summary["by_cell_mode"]["follow"]["count"] == 2
    assert summary["by_regime"]["(0, 0)"]["count"] == 2
