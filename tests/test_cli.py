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
