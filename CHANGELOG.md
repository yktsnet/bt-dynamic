# Changelog

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
