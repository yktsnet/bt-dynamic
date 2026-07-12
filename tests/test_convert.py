import json

import pytest

from bt_dynamic.convert import convert_rows, load_rows, main

ROWS = [
    # 2025-01-06T00:00:00 UTC in epoch milliseconds
    {"timestamp": 1736121600000, "open": 150.0, "high": 150.1, "low": 149.9, "close": 150.05},
    {"timestamp": 1736125200000, "open": 150.05, "high": 150.2, "low": 150.0, "close": 150.1},
]


def test_convert_rows():
    bars = convert_rows(ROWS)
    assert bars[0]["time_utc"] == "2025-01-06T00:00:00"
    assert bars[1]["time_utc"] == "2025-01-06T01:00:00"
    assert bars[0]["open"] == 150.0
    assert set(bars[0]) == {"time_utc", "open", "high", "low", "close"}


def test_load_rows_json(tmp_path):
    path = tmp_path / "bars.json"
    path.write_text(json.dumps(ROWS))
    assert len(load_rows(path)) == 2


def test_load_rows_csv(tmp_path):
    path = tmp_path / "bars.csv"
    path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "1736121600000,150.0,150.1,149.9,150.05,100\n"
    )
    bars = convert_rows(load_rows(path))
    assert bars[0]["time_utc"] == "2025-01-06T00:00:00"


def test_load_rows_empty(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("")
    with pytest.raises(ValueError, match="empty input"):
        load_rows(path)


def test_main_end_to_end(tmp_path, capsys):
    src = tmp_path / "fetched.json"
    src.write_text(json.dumps(ROWS))
    out = tmp_path / "bars.jsonl"

    assert main([str(src), "-o", str(out)]) == 0
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["time_utc"] == "2025-01-06T00:00:00"
