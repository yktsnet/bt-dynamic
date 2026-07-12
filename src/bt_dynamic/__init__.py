"""bt-dynamic: backtest engine for dynamic regime switching.

The market is classified into a 9-cell grid (trend strength x volatility,
3 levels each) plus a direction bias. Each cell maps to an entry mode --
``follow`` (trade with the direction bias), ``flip`` (trade against it) or
``None`` (stay flat). The cell-to-mode mapping and every threshold live in
an external JSON config injected at run time; the package ships no strategy.
"""

from bt_dynamic.config import Config, Params
from bt_dynamic.data import load_jsonl
from bt_dynamic.engine import run_day, summarize
from bt_dynamic.indicators import DEFAULT_INDICATORS, IndicatorSet
from bt_dynamic.regime import classify

__all__ = [
    "Config",
    "Params",
    "load_jsonl",
    "run_day",
    "summarize",
    "DEFAULT_INDICATORS",
    "IndicatorSet",
    "classify",
]
