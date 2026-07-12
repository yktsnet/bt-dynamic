"""Bar data loading.

The repo ships no market data. Users fetch bars themselves (e.g. from
Dukascopy or Alpha Vantage) and provide them as JSONL, one bar per line:

    {"time_utc": "2025-01-06T00:00:00", "open": ..., "high": ..., "low": ..., "close": ...}
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close"]


def load_jsonl(path: str | Path) -> pd.DataFrame:
    """Load JSONL bars into an OHLC DataFrame indexed by UTC time."""
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if not rows:
        raise ValueError(f"no bars in {path}")

    df = pd.DataFrame(rows)
    missing = [c for c in ["time_utc", *REQUIRED_COLUMNS] if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing column(s): {', '.join(missing)}")

    df["time"] = pd.to_datetime(df["time_utc"])
    return df.set_index("time").sort_index()[REQUIRED_COLUMNS]
