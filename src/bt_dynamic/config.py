"""External configuration: parameters and the regime-strategy mapping.

Nothing is loaded at import time. Callers load a JSON file explicitly with
``Config.load(path)`` (or via the ``BT_DYNAMIC_CONFIG`` environment
variable), which keeps production values out of the package and the repo.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

ENV_CONFIG_PATH = "BT_DYNAMIC_CONFIG"

ENTRY_MODES = ("follow", "flip")

LOT_METHODS = ("flat", "proportional", "inverse")

# pre-OSS config keys -> current generic names, used only for error hints
LEGACY_PARAM_NAMES = {
    "adx_weak": "ax1_weak",
    "adx_strong": "ax1_strong",
    "rsi_band": "direction_band",
    "atr_mean_bars": "ax2_mean_bars",
}

Cell = tuple[int, int]


@dataclass(frozen=True)
class Params:
    """Engine and classification parameters with neutral defaults."""

    # engine
    commission_pips: float = 0.3
    bars_per_window: int = 6
    ax2_mean_bars: int = 48
    trade_end_hour: int = 17
    tp_pips: float = 20.0
    sl_pips: float = 10.0
    pip: float = 0.01
    # classification thresholds (axis 1 = trend strength, axis 2 = volatility
    # ratio, direction = oscillator centered on direction_center)
    ax1_weak: float = 20.0
    ax1_strong: float = 25.0
    vol_lo: float = 0.8
    vol_hi: float = 1.2
    direction_band: float = 5.0
    direction_center: float = 50.0


@dataclass(frozen=True)
class Config:
    params: Params
    regime_strategy: dict[Cell, str | None]
    # cell -> sizing method; empty means unit lots (see bt_dynamic.sizing)
    lot_strategy: dict[Cell, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load a config JSON from ``path`` or ``$BT_DYNAMIC_CONFIG``."""
        if path is None:
            path = os.environ.get(ENV_CONFIG_PATH)
        if path is None:
            raise FileNotFoundError(
                "no config given: pass a path or set $BT_DYNAMIC_CONFIG"
            )
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"config file not found: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, source=str(config_path))

    @classmethod
    def from_dict(cls, data: dict, source: str = "<dict>") -> "Config":
        raw_params = data.get("parameters", {})
        known = {f.name for f in fields(Params)}
        unknown = set(raw_params) - known
        if unknown:
            hints = [
                f"{key} -> {LEGACY_PARAM_NAMES[key]}"
                for key in sorted(unknown)
                if key in LEGACY_PARAM_NAMES
            ]
            hint = f" (renamed: {', '.join(hints)})" if hints else ""
            raise ValueError(
                f"{source}: unknown parameter(s): {', '.join(sorted(unknown))}{hint}"
            )
        params = Params(**raw_params)

        strategy = _parse_cell_map(
            data.get("regime_strategy", {}), source, "regime_strategy",
            ENTRY_MODES, allow_null=True,
        )
        lot_strategy = _parse_cell_map(
            data.get("lot_strategy", {}), source, "lot_strategy",
            LOT_METHODS, allow_null=False,
        )
        return cls(params=params, regime_strategy=strategy, lot_strategy=lot_strategy)

    def override(self, **overrides) -> "Config":
        """Return a copy with some parameters replaced (e.g. from CLI ``--param``)."""
        return replace(self, params=replace(self.params, **overrides))


def parse_param_overrides(pairs: list[str]) -> dict:
    """Parse ``["tp_pips=15", "ax1_weak=20"]`` into typed parameter overrides."""
    defaults = Params()
    known = {f.name for f in fields(Params)}
    overrides = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ValueError(f"--param expects key=value, got {pair!r}")
        if key not in known:
            raise ValueError(
                f"unknown parameter {key!r} (known: {', '.join(sorted(known))})"
            )
        overrides[key] = type(getattr(defaults, key))(value)
    return overrides


def _parse_cell_map(
    raw: dict, source: str, name: str, allowed: tuple[str, ...], allow_null: bool
) -> dict[Cell, str | None]:
    """Convert ``{"0,1": "flip", ...}`` keys into ``{(0, 1): "flip", ...}``."""
    parsed: dict[Cell, str | None] = {}
    for key, value in raw.items():
        try:
            ax1, ax2 = (int(x) for x in key.split(","))
        except ValueError:
            raise ValueError(
                f"{source}: {name} key must be 'ax1,ax2', got {key!r}"
            ) from None
        if (value is None and not allow_null) or (
            value is not None and value not in allowed
        ):
            null_hint = " or null" if allow_null else ""
            raise ValueError(
                f"{source}: {name} value must be one of {allowed}{null_hint}, "
                f"got {value!r} for cell {key!r}"
            )
        parsed[(ax1, ax2)] = value
    return parsed
