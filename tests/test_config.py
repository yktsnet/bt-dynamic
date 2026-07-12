import json

import pytest

from bt_dynamic.config import Config, Params


def test_load_example_config(tmp_path):
    data = {
        "parameters": {"ax1_weak": 20.0, "ax1_strong": 30.0, "tp_pips": 15.0},
        "regime_strategy": {"0,0": "flip", "2,1": "follow", "1,1": None},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))

    config = Config.load(path)

    assert config.params.ax1_weak == 20.0
    assert config.params.ax1_strong == 30.0
    assert config.params.tp_pips == 15.0
    # unspecified parameters fall back to neutral defaults
    assert config.params.pip == Params().pip

    assert config.regime_strategy[(0, 0)] == "flip"
    assert config.regime_strategy[(2, 1)] == "follow"
    assert config.regime_strategy[(1, 1)] is None
    # unlisted cells are simply absent; the engine treats them as flat
    assert (0, 1) not in config.regime_strategy


def test_env_var_fallback(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"parameters": {}, "regime_strategy": {}}))
    monkeypatch.setenv("BT_DYNAMIC_CONFIG", str(path))

    config = Config.load()
    assert config.params == Params()


def test_no_config_path_raises(monkeypatch):
    monkeypatch.delenv("BT_DYNAMIC_CONFIG", raising=False)
    with pytest.raises(FileNotFoundError):
        Config.load()


def test_unknown_parameter_rejected():
    with pytest.raises(ValueError, match="unknown parameter"):
        Config.from_dict({"parameters": {"tp_pip": 30.0}})


def test_bad_strategy_key_rejected():
    with pytest.raises(ValueError, match="regime_strategy key"):
        Config.from_dict({"regime_strategy": {"strong": "follow"}})


def test_bad_entry_mode_rejected():
    with pytest.raises(ValueError, match="entry mode"):
        Config.from_dict({"regime_strategy": {"0,0": "reverse"}})
