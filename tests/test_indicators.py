import numpy as np
import pandas as pd
import pytest

from bt_dynamic.indicators import compute_adx, compute_atr, compute_rsi


def _bars(opens, closes, index=None):
    opens = pd.Series(opens)
    closes = pd.Series(closes)
    highs = pd.concat([opens, closes], axis=1).max(axis=1) + 0.01
    lows = pd.concat([opens, closes], axis=1).min(axis=1) - 0.01
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes})
    if index is not None:
        df.index = index
    return df


def test_compute_atr_zero_for_flat_bars():
    df = _bars([100.0] * 30, [100.0] * 30)
    df["high"] = 100.0
    df["low"] = 100.0
    assert (compute_atr(df) == 0.0).all()


def test_compute_adx_higher_for_stronger_trend():
    rng = np.random.default_rng(1)
    flat_open = 100 + rng.normal(0, 0.001, 60)
    flat_close = 100 + rng.normal(0, 0.001, 60)
    noisy_flat = _bars(flat_open, flat_close)

    strong_open = np.linspace(100, 130, 60)
    strong_close = strong_open + 0.05
    strong_trend = _bars(strong_open, strong_close)

    assert compute_adx(strong_trend).iloc[-1] > compute_adx(noisy_flat).iloc[-1]


def _seeded_walk_bars():
    """seed 固定のランダムウォーク。参照値テストの共通入力。"""
    rng = np.random.default_rng(42)
    steps = rng.normal(0.05, 0.4, 40).round(3)
    closes = 100 + np.cumsum(steps)
    opens = np.concatenate([[100.0], closes[:-1]])
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes) + 0.15,
            "low": np.minimum(opens, closes) - 0.15,
            "close": closes,
        }
    )


def test_indicator_reference_values():
    # 既知入力に対する現行実装の値を契約として固定する（計算式の黙った変更を検出する）
    df = _seeded_walk_bars()
    assert compute_atr(df).iloc[20] == pytest.approx(0.5283656237627854)
    assert compute_atr(df).iloc[-1] == pytest.approx(0.5715478873296775)
    assert compute_adx(df).iloc[20] == pytest.approx(34.801697801807336)
    assert compute_adx(df).iloc[-1] == pytest.approx(32.59521751741957)
    assert compute_rsi(df).iloc[20] == pytest.approx(57.2736285211243)
    assert compute_rsi(df).iloc[-1] == pytest.approx(62.66291438652425)


def test_compute_rsi_reflects_direction():
    up_open = np.linspace(100, 110, 30)
    up = _bars(up_open, up_open + 0.05)
    down_open = np.linspace(110, 100, 30)
    down = _bars(down_open, down_open - 0.05)

    assert compute_rsi(up).iloc[-1] > 50
    assert compute_rsi(down).iloc[-1] < 50
