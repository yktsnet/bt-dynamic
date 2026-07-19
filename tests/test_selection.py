from datetime import date

import pandas as pd
import pytest

from bt_dynamic.selection import (
    business_days,
    daily_axis_mean,
    rank_dates,
    sample_dates,
    season_range,
)


def _frame(day_values: dict[date, float]) -> pd.DataFrame:
    """One bar per hour for each day, with a constant axis proxy in 'close'."""
    rows, index = [], []
    for day, value in day_values.items():
        for hour in range(6):
            index.append(pd.Timestamp(day) + pd.Timedelta(hours=hour))
            rows.append({"close": value})
    return pd.DataFrame(rows, index=pd.DatetimeIndex(index))


def _axis(df: pd.DataFrame) -> pd.Series:
    return df["close"]


def test_business_days_skips_weekends():
    # 2024-01-05 is a Friday
    days = business_days(date(2024, 1, 5), 3)
    assert days == [date(2024, 1, 5), date(2024, 1, 8), date(2024, 1, 9)]


def test_season_range_starts_on_business_day():
    # 2025-02-01 is a Saturday -> shifted to Monday 2025-02-03
    start, n = season_range(2025, "spring")
    assert start == date(2025, 2, 3)
    assert n == 65


def test_unknown_season_rejected():
    with pytest.raises(ValueError, match="unknown season"):
        season_range(2025, "monsoon")


def test_daily_axis_mean():
    df = _frame({date(2024, 1, 8): 10.0, date(2024, 1, 9): 30.0})
    assert daily_axis_mean(df, date(2024, 1, 9), _axis) == 30.0


def test_daily_axis_mean_missing_day_is_nan():
    df = _frame({date(2024, 1, 8): 10.0})
    assert pd.isna(daily_axis_mean(df, date(2024, 1, 10), _axis))


def test_rank_dates_descending_and_drops_missing():
    df = _frame(
        {date(2024, 1, 8): 10.0, date(2024, 1, 9): 30.0, date(2024, 1, 10): 20.0}
    )
    dates = [
        date(2024, 1, 8),
        date(2024, 1, 9),
        date(2024, 1, 10),
        date(2024, 1, 11),  # no data
    ]
    assert rank_dates(df, dates, _axis) == [
        date(2024, 1, 9),
        date(2024, 1, 10),
        date(2024, 1, 8),
    ]


def test_sample_dates_reproducible_and_capped():
    dates = business_days(date(2024, 1, 1), 10)
    assert sample_dates(dates, 3, seed=42) == sample_dates(dates, 3, seed=42)
    assert len(sample_dates(dates, 3, seed=42)) == 3
    assert sorted(sample_dates(dates, 99, seed=1)) == sorted(dates)
