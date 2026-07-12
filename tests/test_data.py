import json

import pytest

from bt_dynamic.data import load_jsonl


def test_load_jsonl(tmp_path):
    path = tmp_path / "bars.jsonl"
    rows = [
        {"time_utc": "2025-01-06T00:05:00", "open": 150.0, "high": 150.1, "low": 149.9, "close": 150.05},
        {"time_utc": "2025-01-06T00:00:00", "open": 149.9, "high": 150.0, "low": 149.8, "close": 150.0},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    df = load_jsonl(path)

    assert list(df.columns) == ["open", "high", "low", "close"]
    assert df.index.is_monotonic_increasing  # sorted even if input is not
    assert len(df) == 2


def test_load_jsonl_missing_column(tmp_path):
    path = tmp_path / "bars.jsonl"
    path.write_text(json.dumps({"time_utc": "2025-01-06T00:00:00", "open": 1.0}) + "\n")
    with pytest.raises(ValueError, match="missing column"):
        load_jsonl(path)


def test_load_jsonl_empty(tmp_path):
    path = tmp_path / "bars.jsonl"
    path.write_text("")
    with pytest.raises(ValueError, match="no bars"):
        load_jsonl(path)
