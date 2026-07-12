"""Single-day backtest engine.

- The previous business day warms up the indicators.
- Every ``bars_per_window`` bars inside the trade window the regime is
  classified and the config's regime_strategy decides follow / flip / flat.
- Entries fill at the next bar's open with a fixed TP/SL bracket (OCO);
  open positions are force-closed at ``trade_end_hour``.
- Commission is charged in pips on exit.

The engine knows nothing about concrete indicators or strategies: indicators
come in as an :class:`~bt_dynamic.indicators.IndicatorSet`, thresholds and
the cell-to-mode mapping come in as a :class:`~bt_dynamic.config.Config`.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from bt_dynamic.config import Cell, Config, Params
from bt_dynamic.indicators import DEFAULT_INDICATORS, IndicatorSet
from bt_dynamic.regime import classify


def _previous_business_days(target: date, count: int) -> list[date]:
    days: list[date] = []
    current = target - timedelta(days=1)
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))


def calc_result_pips(
    direction: str, entry_price: float, exit_price: float, pip: float
) -> float:
    if direction == "BUY":
        return (exit_price - entry_price) / pip
    return (entry_price - exit_price) / pip


def _check_exit(pos: dict, bar) -> tuple[str | None, float | None]:
    if pos["direction"] == "BUY":
        if bar["low"] <= pos["sl"]:
            return "SL", pos["sl"]
        if bar["high"] >= pos["tp"]:
            return "TP", pos["tp"]
    else:
        if bar["high"] >= pos["sl"]:
            return "SL", pos["sl"]
        if bar["low"] <= pos["tp"]:
            return "TP", pos["tp"]
    return None, None


def resolve_entry(
    price: float,
    cell_mode: str | None,
    direction: str | None,
    params: Params,
) -> dict | None:
    """Turn a cell mode and direction bias into an order, or ``None`` to stay flat."""
    if cell_mode is None or direction is None:
        return None

    actual = (
        direction if cell_mode == "follow" else "SELL" if direction == "BUY" else "BUY"
    )
    tp_dist = params.tp_pips * params.pip
    sl_dist = params.sl_pips * params.pip

    if actual == "BUY":
        sl, tp = price - sl_dist, price + tp_dist
    else:
        sl, tp = price + sl_dist, price - tp_dist

    return {
        "direction": actual,
        "entry_price": price,
        "sl": sl,
        "tp": tp,
        "cell_mode": cell_mode,
    }


def _static_thresholds(params: Params) -> dict:
    return {
        "ax1_weak": params.ax1_weak,
        "ax1_strong": params.ax1_strong,
        "vol_lo": params.vol_lo,
        "vol_hi": params.vol_hi,
    }


def _dynamic_thresholds(
    df_warm: pd.DataFrame,
    target: date,
    lookback_days: int,
    params: Params,
    indicators: IndicatorSet,
) -> dict | None:
    """Derive ax1/vol thresholds from recent decision-point percentiles."""
    past_days = set(_previous_business_days(target, lookback_days))
    df_past = df_warm[pd.Index(df_warm.index.date).isin(past_days)]
    df_past = df_past[df_past.index.hour < params.trade_end_hour]
    if len(df_past) < params.bars_per_window:
        return None

    ax1_s = indicators.compute_ax1(df_warm).reindex(df_past.index)
    ax2_full_s = indicators.compute_ax2(df_warm)
    ax2_s = ax2_full_s.reindex(df_past.index)
    ax2_mean_s = indicators.compute_ax2_mean(
        ax2_full_s, params.ax2_mean_bars
    ).reindex(df_past.index)

    decision_indexes = []
    for day in past_days:
        day_indexes = df_past.index[df_past.index.date == day]
        decision_indexes.extend(
            day_indexes[params.bars_per_window :: params.bars_per_window]
        )
    if not decision_indexes:
        return None

    ax1_vals = ax1_s.reindex(decision_indexes).dropna()
    ratios = (ax2_s / ax2_mean_s).replace([np.inf, -np.inf], np.nan)
    ratio_vals = ratios.reindex(decision_indexes).dropna()
    if ax1_vals.empty or ratio_vals.empty:
        return None

    ax1_weak, ax1_strong = np.percentile(ax1_vals.to_numpy(), [33, 67])
    vol_lo, vol_hi = np.percentile(ratio_vals.to_numpy(), [33, 67])
    return {
        "ax1_weak": float(ax1_weak),
        "ax1_strong": float(ax1_strong),
        "vol_lo": float(vol_lo),
        "vol_hi": float(vol_hi),
    }


def run_day(
    df: pd.DataFrame,
    date_str: str,
    config: Config,
    indicators: IndicatorSet = DEFAULT_INDICATORS,
    use_dynamic: bool = False,
    lookback_days: int = 3,
    dynamic_cells: set[Cell] | None = None,
    multi_position: bool = False,
) -> list[dict]:
    """Backtest one day and return the closed trades."""
    params = config.params
    target = pd.Timestamp(date_str).date()

    prev = target - pd.Timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= pd.Timedelta(days=1)

    df_warm = df[df.index.date >= prev]
    df_trade = df_warm[df_warm.index.date == target]

    if len(df_trade) < params.bars_per_window * 2:
        return []

    ax1_s = indicators.compute_ax1(df_warm)
    ax2_s = indicators.compute_ax2(df_warm)
    dir_s = indicators.compute_direction(df_warm)
    ax2_mean_s = indicators.compute_ax2_mean(ax2_s, params.ax2_mean_bars)

    if use_dynamic:
        dynamic_prev = _previous_business_days(target, lookback_days + 1)[0]
        df_dynamic_warm = df[df.index.date >= dynamic_prev]
        dynamic_thresholds = _dynamic_thresholds(
            df_dynamic_warm, target, lookback_days, params, indicators
        )
    else:
        dynamic_thresholds = None

    ax1_s = ax1_s.reindex(df_trade.index)
    ax2_s = ax2_s.reindex(df_trade.index)
    dir_s = dir_s.reindex(df_trade.index)
    ax2_mean_s = ax2_mean_s.reindex(df_trade.index)

    df_window = df_trade[df_trade.index.hour < params.trade_end_hour]
    n = len(df_window)
    if n < params.bars_per_window:
        return []

    static_thresholds = _static_thresholds(params)
    direction_kwargs = {
        "direction_band": params.direction_band,
        "direction_center": params.direction_center,
    }

    trades: list[dict] = []
    active: dict | None = None
    actives: list[dict] = []
    decision_points = set(range(params.bars_per_window, n, params.bars_per_window))

    def close(pos: dict, exit_time, exit_price: float, kind: str) -> None:
        result = (
            calc_result_pips(pos["direction"], pos["entry_price"], exit_price, params.pip)
            - params.commission_pips
        )
        trades.append(
            {
                **pos,
                "exit_time": exit_time,
                "exit_price": exit_price,
                "result_pips": result,
                "exit": kind,
            }
        )

    for bar_idx in range(params.bars_per_window, n):
        bar = df_window.iloc[bar_idx]
        bar_time = df_window.index[bar_idx]
        orig_idx = df_trade.index.get_loc(bar_time)

        if multi_position:
            remaining = []
            for pos in actives:
                hit, exit_price = _check_exit(pos, bar)
                if hit:
                    close(pos, bar_time, exit_price, hit)
                else:
                    remaining.append(pos)
            actives = remaining
        elif active is not None:
            hit, exit_price = _check_exit(active, bar)
            if hit:
                close(active, bar_time, exit_price, hit)
                active = None

        can_enter = multi_position or active is None
        if bar_idx in decision_points and can_enter:
            ax1_v = ax1_s.iloc[orig_idx]
            ax2_v = ax2_s.iloc[orig_idx]
            ax2_mean_v = ax2_mean_s.iloc[orig_idx]
            dir_v = dir_s.iloc[orig_idx]

            if any(pd.isna(v) for v in [ax1_v, ax2_v, ax2_mean_v, dir_v]):
                continue

            ax1_static, ax2_static, _ = classify(
                ax1_v, ax2_v, ax2_mean_v, dir_v,
                **static_thresholds, **direction_kwargs,
            )
            should_use_dynamic = dynamic_thresholds is not None and (
                dynamic_cells is None or (ax1_static, ax2_static) in dynamic_cells
            )
            thresholds = dynamic_thresholds if should_use_dynamic else static_thresholds
            ax1_class, ax2_class, direction = classify(
                ax1_v, ax2_v, ax2_mean_v, dir_v, **thresholds, **direction_kwargs
            )
            cell_mode = config.regime_strategy.get((ax1_class, ax2_class))

            if bar_idx + 1 >= n:
                continue
            next_bar = df_window.iloc[bar_idx + 1]
            next_bar_time = df_window.index[bar_idx + 1]
            entry = resolve_entry(next_bar["open"], cell_mode, direction, params)
            if not entry:
                continue

            trade = {
                **entry,
                "entry_time": next_bar_time,
                "regime": (ax1_class, ax2_class),
                "ax1": round(float(ax1_v), 1),
                "ax2": round(float(ax2_v), 5),
                "direction_val": round(float(dir_v), 1),
            }
            if multi_position:
                # An opposite-direction signal offsets existing positions.
                new_dir = entry["direction"]
                remaining = []
                for pos in actives:
                    if pos["direction"] != new_dir:
                        close(pos, next_bar_time, next_bar["open"], "OFFSET")
                    else:
                        remaining.append(pos)
                actives = remaining
                actives.append(trade)
            else:
                active = trade

    last = df_window.iloc[-1]
    last_time = df_window.index[-1]
    if multi_position:
        for pos in actives:
            close(pos, last_time, last["close"], "EOD")
    elif active is not None:
        close(active, last_time, last["close"], "EOD")

    return trades


def summarize_dict(trades: list[dict]) -> dict:
    """Summarize trades as plain data, for ``--json`` output and run comparison."""
    if not trades:
        return {"trades": 0}

    df = pd.DataFrame(trades)

    def breakdown(col: str) -> dict:
        agg = df.groupby(col)["result_pips"].agg(["count", "sum", "mean"])
        return {
            str(key): {
                "count": int(row["count"]),
                "sum": round(float(row["sum"]), 2),
                "mean": round(float(row["mean"]), 2),
            }
            for key, row in agg.iterrows()
        }

    wins = int((df["result_pips"] > 0).sum())
    return {
        "trades": len(df),
        "wins": wins,
        "losses": len(df) - wins,
        "win_rate": round(wins / len(df), 3),
        "total_pips": round(float(df["result_pips"].sum()), 2),
        "avg_pips": round(float(df["result_pips"].mean()), 2),
        "best_pips": round(float(df["result_pips"].max()), 2),
        "worst_pips": round(float(df["result_pips"].min()), 2),
        "by_exit": breakdown("exit"),
        "by_cell_mode": breakdown("cell_mode"),
        "by_regime": breakdown("regime"),
    }


def summarize(trades: list[dict]) -> pd.DataFrame | None:
    """Print a result summary and return the trades as a DataFrame."""
    if not trades:
        print("no trades")
        return None

    df = pd.DataFrame(trades)
    total = df["result_pips"].sum()
    wins = (df["result_pips"] > 0).sum()
    print(f"\n{'=' * 50}")
    print(f"trades    : {len(df)}")
    print(f"win rate  : {wins / len(df) * 100:.1f}% ({wins}W {len(df) - wins}L)")
    print(f"total pips: {total:.2f}")
    print(f"avg pips  : {df['result_pips'].mean():.2f}")
    print(f"best      : {df['result_pips'].max():.2f}")
    print(f"worst     : {df['result_pips'].min():.2f}")
    print("\n--- by exit ---")
    print(df.groupby("exit")["result_pips"].agg(["count", "sum", "mean"]).round(2))
    print("\n--- by cell mode ---")
    print(df.groupby("cell_mode")["result_pips"].agg(["count", "sum", "mean"]).round(2))
    print("\n--- by regime ---")
    print(df.groupby("regime")["result_pips"].agg(["count", "sum", "mean"]).round(2))
    print(f"{'=' * 50}\n")
    return df
