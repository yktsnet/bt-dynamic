"""Command-line entry point: ``bt-dynamic``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta

from bt_dynamic.config import Config, parse_param_overrides
from bt_dynamic.data import load_jsonl
from bt_dynamic.engine import run_day, summarize, summarize_dict
from bt_dynamic.indicators import DEFAULT_INDICATORS, load_indicator_file


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="bt-dynamic",
        description=(
            "Backtest a dynamic regime-switching strategy over JSONL bars. "
            "All thresholds and the cell-to-mode mapping come from the config JSON."
        ),
    )
    p.add_argument(
        "--config",
        default=None,
        help="config JSON path (default: $BT_DYNAMIC_CONFIG)",
    )
    p.add_argument("--data", required=True, help="JSONL bar data path")
    p.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="override a config parameter for this run (repeatable), "
        "e.g. --param tp_pips=15 --param ax1_weak=20",
    )
    p.add_argument(
        "--indicators",
        default=None,
        metavar="FILE.py",
        help="Python file defining INDICATORS = IndicatorSet(...) to replace the "
        "default ADX/ATR/RSI",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="print a machine-readable JSON summary instead of the text report",
    )
    p.add_argument(
        "--start",
        default=None,
        help="first trade date YYYY-MM-DD (default: first date in data with a warmup day)",
    )
    p.add_argument(
        "--days",
        type=int,
        default=None,
        help="number of business days to run (default: through end of data)",
    )
    p.add_argument(
        "--dynamic",
        action="store_true",
        help="derive ax1/vol thresholds from recent percentiles instead of static config values",
    )
    p.add_argument(
        "--lookback",
        type=int,
        default=3,
        help="lookback business days for --dynamic (default: 3)",
    )
    p.add_argument(
        "--multi",
        action="store_true",
        help="allow multiple positions (opposite signals offset)",
    )
    p.add_argument(
        "--quiet", action="store_true", help="suppress per-trade lines, summary only"
    )
    return p.parse_args(argv)


def _business_days_from(start: date, end: date, limit: int | None) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end and (limit is None or len(days) < limit):
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = Config.load(args.config)
        overrides = parse_param_overrides(args.param)
        if overrides:
            config = config.override(**overrides)
        indicators = (
            load_indicator_file(args.indicators)
            if args.indicators
            else DEFAULT_INDICATORS
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    df = load_jsonl(args.data)

    dates = sorted(set(df.index.date))
    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
    else:
        # the first date in the data only warms up the indicators
        if len(dates) < 2:
            print("data must span at least 2 days (first day is warmup)", file=sys.stderr)
            return 1
        start = dates[1]
    targets = _business_days_from(start, dates[-1], args.days)

    all_trades = []
    for target in targets:
        trades = run_day(
            df,
            str(target),
            config,
            indicators=indicators,
            use_dynamic=args.dynamic,
            lookback_days=args.lookback,
            multi_position=args.multi,
        )
        all_trades.extend(trades)
        if args.quiet or args.json:
            continue
        print(f"--- {target} ({target.strftime('%a')}) : {len(trades)} trade(s) ---")
        for t in trades:
            print(
                f"  {t['entry_time'].strftime('%H:%M')}->{t['exit_time'].strftime('%H:%M')} "
                f"{t['direction']:4s} {t['cell_mode']:6s} "
                f"regime=({t['regime'][0]},{t['regime'][1]}) "
                f"{t['result_pips']:+.2f}pips [{t['exit']}]"
            )

    if args.json:
        result = {
            "meta": {
                "config": args.config,
                "data": args.data,
                "start": str(start),
                "days": args.days,
                "dynamic": args.dynamic,
                "multi": args.multi,
                "indicators": args.indicators,
                "param_overrides": overrides,
            },
            "summary": summarize_dict(all_trades),
        }
        print(json.dumps(result, ensure_ascii=False))
    else:
        summarize(all_trades)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
