"""Default indicator set (ADX / ATR / RSI) and the injection point for custom ones.

The engine only knows the abstract axes: ``ax1`` (trend strength), ``ax2``
(volatility) and ``direction`` (an oscillator centered on 50). Swap in your
own indicators by passing a different :class:`IndicatorSet` to ``run_day``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    return dx.ewm(span=period, adjust=False).mean()


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    return 100 - 100 / (1 + gain / (loss + 1e-9))


@dataclass(frozen=True)
class IndicatorSet:
    """Indicator functions mapped onto the engine's abstract axes."""

    compute_ax1: Callable[[pd.DataFrame], pd.Series]
    compute_ax2: Callable[[pd.DataFrame], pd.Series]
    compute_direction: Callable[[pd.DataFrame], pd.Series]

    def compute_ax2_mean(self, ax2_s: pd.Series, bars: int) -> pd.Series:
        """Rolling mean of ax2, used as the denominator of the volatility ratio."""
        return ax2_s.rolling(bars, min_periods=4).mean()


DEFAULT_INDICATORS = IndicatorSet(
    compute_ax1=compute_adx,
    compute_ax2=compute_atr,
    compute_direction=compute_rsi,
)
