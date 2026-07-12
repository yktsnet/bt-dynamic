"""Generate synthetic sample bars for the example.

The output is a seeded random walk that alternates trending and ranging
phases so the 9-cell classification exercises a variety of cells. It is not
market data and resembles no real instrument.

Usage: python generate_data.py  (rewrites data/sample_m5.jsonl)
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT_PATH = Path(__file__).parent / "data" / "sample_m5.jsonl"
SEED = 42

START = datetime(2025, 1, 6)  # Monday
DAYS = 5
BARS_PER_DAY = 252  # 00:00 - 20:55 UTC, 5-minute bars
BASE_PRICE = 150.0

# (drift per bar, volatility per bar), cycled through the week
PHASES = [
    (0.004, 0.010),   # steady uptrend
    (0.0, 0.006),     # quiet range
    (-0.006, 0.020),  # volatile downtrend
    (0.0, 0.015),     # volatile range
    (0.002, 0.008),   # mild uptrend
]
PHASE_BARS = 120


def generate() -> list[dict]:
    rng = random.Random(SEED)
    price = BASE_PRICE
    bars = []
    bar_count = 0

    for day in range(DAYS):
        day_start = START + timedelta(days=day)
        for i in range(BARS_PER_DAY):
            drift, vol = PHASES[(bar_count // PHASE_BARS) % len(PHASES)]
            open_ = price
            close = open_ + drift + rng.gauss(0, vol)
            high = max(open_, close) + abs(rng.gauss(0, vol * 0.5))
            low = min(open_, close) - abs(rng.gauss(0, vol * 0.5))
            price = close
            bar_count += 1
            bars.append(
                {
                    "time_utc": (day_start + timedelta(minutes=5 * i)).isoformat(),
                    "open": round(open_, 3),
                    "high": round(high, 3),
                    "low": round(low, 3),
                    "close": round(close, 3),
                }
            )
    return bars


def main() -> None:
    bars = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for bar in bars:
            f.write(json.dumps(bar) + "\n")
    print(f"wrote {len(bars)} bars to {OUT_PATH}")


if __name__ == "__main__":
    main()
