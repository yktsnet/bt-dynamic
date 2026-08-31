# Changelog

## 0.2.1

- `validation`: add `paired_diff(bars, dates, baseline, candidate)` — day-paired diff (candidate minus baseline) with mean/std/stderr/t-stat/95% CI, reusing `engine.dispersion` on the daily diff series. Pairing index is the given dates, so a day where only one side traded still counts, as 0.0 for the side that stayed flat; this makes the interval narrower than combining the two configs' independent summaries would, since it cancels the noise they share
- `param_sweep`: each result now also carries `diff_vs_base`, the same day-paired diff against the empty-override candidate, computed from the `trades` already collected rather than re-running the backtest

## 0.2.0

- `summarize_dict`: every summary now carries the spread of per-trade P&L — `std_pips`, `stderr_pips`, `t_stat` and the 95% interval on the mean (`ci95_low` / `ci95_high`). A total alone cannot tell an edge from noise. Exposed as `dispersion()` for direct use; `summarize()` prints it too
- `param_sweep`: ranks by `t_stat` instead of total pips (**behaviour change**), and each result now carries its `trades` so a candidate can be broken down by year or train/test without re-running the sweep
- `cell_breakdown`: new `cells` argument scores cells the config leaves flat; the default still covers only the configured ones
- `regime.ALL_CELLS`: the full 3x3 grid, for scanning every cell `classify` can return
- `__version__` was stuck at 0.1.0 since the first release; it now tracks the package version

## 0.1.6

- `load_jsonl`: parse `time_utc` per row as ISO8601, so a single file may mix formats (e.g. with and without fractional seconds)

## 0.1.5

- Add `validation` module: multi-day `run_period`, chronological `split_train_test`, per-cell `cell_breakdown`, ranked `param_sweep`

## 0.1.4

- Add `selection` module: business days, seasonal windows, axis-based date ranking, seeded sampling
- Add `sizing` module: post-run lot reweighting (flat / proportional / inverse), mapping injected via `Config.lot_strategy`
- `Config`: new `lot_strategy` field; regime_strategy error message for bad entry modes now reads `regime_strategy value`

## 0.1.3

- Use a short PyPI readme pointing to GitHub

## 0.1.2

- Add CHANGELOG

## 0.1.1

- CI: add PyPI Trusted Publishing workflow (`.github/workflows/publish.yml`)

## 0.1.0

- Initial PyPI release
