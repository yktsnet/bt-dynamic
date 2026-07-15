import numpy as np
import pandas as pd

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


def test_compute_rsi_reflects_direction():
    up_open = np.linspace(100, 110, 30)
    up = _bars(up_open, up_open + 0.05)
    down_open = np.linspace(110, 100, 30)
    down = _bars(down_open, down_open - 0.05)

    assert compute_rsi(up).iloc[-1] > 50
    assert compute_rsi(down).iloc[-1] < 50
