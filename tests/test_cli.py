import json
from pathlib import Path

import pytest

from bt_dynamic.cli import main

EXAMPLE = Path(__file__).parent.parent / "examples" / "trend"


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "usage: bt-dynamic" in capsys.readouterr().out


def test_cli_runs_example(capsys):
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--quiet",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "trades" in out or "no trades" in out


def test_cli_dynamic_mode(capsys):
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--dynamic",
            "--quiet",
        ]
    )
    assert code == 0


def test_cli_param_override_and_json(capsys):
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--param", "tp_pips=5",
            "--param", "sl_pips=5",
            "--json",
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["meta"]["param_overrides"] == {"tp_pips": 5.0, "sl_pips": 5.0}
    assert result["summary"]["trades"] > 0
    assert "by_regime" in result["summary"]


def test_cli_bad_param(capsys):
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--param", "tp_pip=5",
        ]
    )
    assert code == 2
    assert "unknown parameter" in capsys.readouterr().err


def test_cli_custom_indicators(tmp_path, capsys):
    indicator_file = tmp_path / "my_indicators.py"
    indicator_file.write_text(
        "from bt_dynamic.indicators import IndicatorSet, compute_adx, compute_atr, compute_rsi\n"
        "INDICATORS = IndicatorSet(\n"
        "    compute_ax1=compute_adx,\n"
        "    compute_ax2=compute_atr,\n"
        "    compute_direction=compute_rsi,\n"
        ")\n"
    )
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--indicators", str(indicator_file),
            "--quiet",
        ]
    )
    assert code == 0


def test_cli_cells_filter(capsys):
    # the example config only trades cells (0,0) (0,1) (2,1) (2,2);
    # restricting to a never-hit cell must yield zero trades
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--cells", "1,1",
            "--json",
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["trades"] == 0


def test_cli_bad_cells(capsys):
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--cells", "strong",
        ]
    )
    assert code == 2
    assert "--cells" in capsys.readouterr().err


def test_cli_debug_dump(capsys):
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--start", "2025-01-09",
            "--days", "1",
            "--debug",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "decision points" in out
    assert "ENTRY" in out or "skip(" in out


def test_cli_multiple_data_files(tmp_path, capsys):
    # split the sample into two files; concatenation must behave like the whole
    lines = (EXAMPLE / "data" / "sample_m5.jsonl").read_text().strip().splitlines()
    half = len(lines) // 2
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_text("\n".join(lines[:half]) + "\n")
    b.write_text("\n".join(lines[half:]) + "\n")

    for data_args in ([str(a), str(b)], [str(EXAMPLE / "data" / "sample_m5.jsonl")]):
        code = main(["--config", str(EXAMPLE / "config.json"), "--data", *data_args, "--json"])
        assert code == 0

    outputs = capsys.readouterr().out.strip().splitlines()
    split_run, whole_run = (json.loads(line)["summary"] for line in outputs)
    assert split_run == whole_run


def test_cli_bad_indicator_file(tmp_path, capsys):
    indicator_file = tmp_path / "bad.py"
    indicator_file.write_text("X = 1\n")
    code = main(
        [
            "--config", str(EXAMPLE / "config.json"),
            "--data", str(EXAMPLE / "data" / "sample_m5.jsonl"),
            "--indicators", str(indicator_file),
        ]
    )
    assert code == 2
    assert "INDICATORS" in capsys.readouterr().err
