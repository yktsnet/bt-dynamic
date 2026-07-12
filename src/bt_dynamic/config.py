"""External configuration: parameters and the regime-strategy mapping.

Nothing is loaded at import time. Callers load a JSON file explicitly with
``Config.load(path)`` (or via the ``BT_DYNAMIC_CONFIG`` environment
variable), which keeps production values out of the package and the repo.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path

ENV_CONFIG_PATH = "BT_DYNAMIC_CONFIG"

ENTRY_MODES = ("follow", "flip")

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
            raise ValueError(
                f"{source}: unknown parameter(s): {', '.join(sorted(unknown))}"
            )
        params = Params(**raw_params)

        strategy = _parse_strategy(data.get("regime_strategy", {}), source)
        return cls(params=params, regime_strategy=strategy)


def _parse_strategy(raw: dict, source: str) -> dict[Cell, str | None]:
    """Convert ``{"0,1": "flip", ...}`` keys into ``{(0, 1): "flip", ...}``."""
    strategy: dict[Cell, str | None] = {}
    for key, mode in raw.items():
        try:
            ax1, ax2 = (int(x) for x in key.split(","))
        except ValueError:
            raise ValueError(
                f"{source}: regime_strategy key must be 'ax1,ax2', got {key!r}"
            ) from None
        if mode is not None and mode not in ENTRY_MODES:
            raise ValueError(
                f"{source}: entry mode must be one of {ENTRY_MODES} or null, "
                f"got {mode!r} for cell {key!r}"
            )
        strategy[(ax1, ax2)] = mode
    return strategy
