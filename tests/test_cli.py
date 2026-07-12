import json
from pathlib import Path

from bt_dynamic.cli import main

EXAMPLE = Path(__file__).parent.parent / "examples" / "trend"


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
