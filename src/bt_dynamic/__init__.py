"""bt-dynamic: backtest engine for dynamic regime switching.

The market is classified into a 9-cell grid (trend strength x volatility,
3 levels each) plus a direction bias. Each cell maps to an entry mode --
``follow`` (trade with the direction bias), ``flip`` (trade against it) or
``None`` (stay flat). The cell-to-mode mapping and every threshold live in
an external JSON config injected at run time; the package ships no strategy.
"""

__version__ = "0.1.0"

from bt_dynamic.config import Config, Params
from bt_dynamic.data import load_jsonl
from bt_dynamic.engine import debug_day, run_day, summarize, summarize_dict
from bt_dynamic.indicators import DEFAULT_INDICATORS, IndicatorSet, load_indicator_file
from bt_dynamic.regime import classify

__all__ = [
    "Config",
    "Params",
    "load_jsonl",
    "run_day",
    "debug_day",
    "summarize",
    "summarize_dict",
    "DEFAULT_INDICATORS",
    "IndicatorSet",
    "load_indicator_file",
    "classify",
]
