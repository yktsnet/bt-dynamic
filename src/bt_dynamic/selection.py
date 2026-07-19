"""Trading-date selection for building backtest samples.

Helpers for picking which days to backtest: calendar ranges (business days,
seasonal windows) and condition-based ranking (sort candidate dates by the
daily mean of any indicator axis). Axis-agnostic like the engine: ranking
takes a compute function (e.g. ``indicators.compute_ax1``) instead of naming
a concrete indicator.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Callable

import pandas as pd

SEASONS = {
    "spring": (2, 1),
    "summer": (6, 1),
    "autumn": (9, 1),
    "winter": (12, 1),
}
SEASON_DAYS = 65


def _previous_business_day(target: date) -> date:
    prev = target - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return prev


def business_days(start: date, n: int) -> list[date]:
    """The first ``n`` business days starting at ``start`` (weekends skipped)."""
    days, current = [], start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def season_range(year: int, season: str) -> tuple[date, int]:
    """Start date and length (in business days) of a seasonal sample window."""
    if season not in SEASONS:
        raise ValueError(
            f"unknown season {season!r} (known: {', '.join(sorted(SEASONS))})"
        )
    month, day = SEASONS[season]
    start = date(year, month, day)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    return start, SEASON_DAYS


def daily_axis_mean(
    df: pd.DataFrame,
    target: date,
    compute_axis: Callable[[pd.DataFrame], pd.Series],
) -> float:
    """Mean of an indicator axis over one trading day.

    The previous business day warms up the indicator, mirroring the engine's
    warm-up so rankings reflect what the engine would actually see.
    """
    prev = _previous_business_day(target)
    df_warm = df[df.index.date >= prev]
    df_trade = df_warm[df_warm.index.date == target]
    if df_trade.empty:
        return float("nan")
    axis_s = compute_axis(df_warm).reindex(df_trade.index)
    return float(axis_s.mean())


def rank_dates(
    df: pd.DataFrame,
    dates: list[date],
    compute_axis: Callable[[pd.DataFrame], pd.Series],
) -> list[date]:
    """Candidate dates sorted by daily axis mean, highest first.

    Dates with no data (NaN mean) are dropped, so the result doubles as the
    set of valid dates for :func:`sample_dates`.
    """
    ranked = [(target, daily_axis_mean(df, target, compute_axis)) for target in dates]
    ranked = [item for item in ranked if not pd.isna(item[1])]
    return [target for target, _ in sorted(ranked, key=lambda item: item[1], reverse=True)]


def sample_dates(dates: list[date], n: int, seed: int) -> list[date]:
    """Reproducible random sample of at most ``n`` dates."""
    rng = random.Random(seed)
    return rng.sample(dates, min(n, len(dates)))
