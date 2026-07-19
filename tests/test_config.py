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


def test_load_malformed_json_raises(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    with pytest.raises(json.JSONDecodeError):
        Config.load(path)


def test_unknown_parameter_rejected():
    with pytest.raises(ValueError, match="unknown parameter"):
        Config.from_dict({"parameters": {"tp_pip": 30.0}})


def test_bad_strategy_key_rejected():
    with pytest.raises(ValueError, match="regime_strategy key"):
        Config.from_dict({"regime_strategy": {"strong": "follow"}})


def test_bad_entry_mode_rejected():
    with pytest.raises(ValueError, match="regime_strategy value"):
        Config.from_dict({"regime_strategy": {"0,0": "reverse"}})


def test_lot_strategy_parsed():
    config = Config.from_dict(
        {"lot_strategy": {"0,0": "flat", "1,0": "inverse", "2,1": "proportional"}}
    )
    assert config.lot_strategy[(0, 0)] == "flat"
    assert config.lot_strategy[(1, 0)] == "inverse"
    assert config.lot_strategy[(2, 1)] == "proportional"


def test_lot_strategy_defaults_empty():
    config = Config.from_dict({"parameters": {}, "regime_strategy": {}})
    assert config.lot_strategy == {}


def test_bad_lot_method_rejected():
    with pytest.raises(ValueError, match="lot_strategy value"):
        Config.from_dict({"lot_strategy": {"0,0": "martingale"}})


def test_null_lot_method_rejected():
    # unlike regime_strategy, "no sizing" is expressed by omitting the cell
    with pytest.raises(ValueError, match="lot_strategy value"):
        Config.from_dict({"lot_strategy": {"0,0": None}})


def test_parse_param_overrides():
    from bt_dynamic.config import parse_param_overrides

    overrides = parse_param_overrides(["tp_pips=15", "bars_per_window=4"])
    assert overrides == {"tp_pips": 15.0, "bars_per_window": 4}
    assert isinstance(overrides["tp_pips"], float)
    assert isinstance(overrides["bars_per_window"], int)

    with pytest.raises(ValueError, match="key=value"):
        parse_param_overrides(["tp_pips"])
    with pytest.raises(ValueError, match="unknown parameter"):
        parse_param_overrides(["tp_pip=15"])


def test_config_override():
    config = Config.from_dict({"parameters": {"tp_pips": 30.0}})
    overridden = config.override(tp_pips=15.0, sl_pips=5.0)

    assert overridden.params.tp_pips == 15.0
    assert overridden.params.sl_pips == 5.0
    assert config.params.tp_pips == 30.0  # original untouched
