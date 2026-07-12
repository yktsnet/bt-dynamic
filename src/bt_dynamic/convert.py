"""Convert fetched bar data into the JSONL format the engine reads.

Supports the output of dukascopy-node (https://github.com/Leo4815162342/dukascopy-node),
either JSON (``-f json``) or CSV (``-f csv``): rows of epoch-millisecond
``timestamp`` plus ``open/high/low/close``. Timestamps are treated as UTC.

Usage: ``bt-dynamic-convert fetched.json -o bars.jsonl``
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def _to_time_utc(timestamp_ms: float) -> str:
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def convert_rows(rows: list[dict]) -> list[dict]:
    bars = []
    for row in rows:
        bars.append(
            {
                "time_utc": _to_time_utc(float(row["timestamp"])),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
        )
    return bars


def load_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"empty input: {path}")
    if text.startswith("["):
        return json.loads(text)
    return list(csv.DictReader(text.splitlines()))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="bt-dynamic-convert",
        description="Convert dukascopy-node JSON/CSV output into bt-dynamic JSONL bars.",
    )
    p.add_argument("input", help="dukascopy-node output file (.json or .csv)")
    p.add_argument("-o", "--output", required=True, help="JSONL output path")
    args = p.parse_args(argv)

    bars = convert_rows(load_rows(Path(args.input)))
    with open(args.output, "w", encoding="utf-8") as f:
        for bar in bars:
            f.write(json.dumps(bar) + "\n")
    print(f"wrote {len(bars)} bars to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
