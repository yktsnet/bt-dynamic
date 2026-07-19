# Guarantee Ledger

## Guarantees

### 1. `tests/test_cli.py` — `bt-dynamic` CLI (`bt_dynamic.cli.main`)

- 正常な config・data を与えると exit code 0 で走り、`trades` または `no trades` を含む出力を返す。`--dynamic` を付けても同様に exit code 0 で走る。
- `--param key=value` は複数指定でき、型（float/int）を保ったまま `--json` 出力の `meta.param_overrides` に反映される。`--json` 出力は `summary.trades` と `summary.by_regime` を含む。未知のキーは exit code 2、stderr に `unknown parameter`。
- `--cells a,b` は対象セルを絞り込め、config が一度も踏まないセルを指定すると `summary.trades == 0`。不正な値は exit code 2、stderr に `--cells`。
- `--indicators file.py` で `IndicatorSet`（`compute_ax1`/`compute_ax2`/`compute_direction`）を外部から差し替えられる。`INDICATORS` が定義されていない場合は exit code 2、stderr に `INDICATORS`。
- `--debug` は判定過程（decision points）を含む出力を返し、各行は `ENTRY` または `skip(...)` で始まる。
- `--data` に複数ファイルを渡すと結合して扱われ、結果は単一ファイルで渡した場合と一致する。
- `--help` は exit code 0 で `usage: bt-dynamic` を含むヘルプを標準出力に返す。

| 保証（要約） | 対応テスト |
|---|---|
| 実行の基本 | `test_cli_runs_example`, `test_cli_dynamic_mode` |
| パラメータ上書き | `test_cli_param_override_and_json`, `test_cli_bad_param` |
| セル絞り込み | `test_cli_cells_filter`, `test_cli_bad_cells` |
| 指標の差し替え | `test_cli_custom_indicators`, `test_cli_bad_indicator_file` |
| デバッグ出力 | `test_cli_debug_dump` |
| 複数データファイルの結合 | `test_cli_multiple_data_files` |
| ヘルプ出力 | `test_cli_help` |

### 2. `tests/test_convert.py` — `bt-dynamic-convert` CLI (`bt_dynamic.convert`)

- epoch ミリ秒の `timestamp` を `time_utc`（ISO 形式）に変換し、`open`/`high`/`low`/`close` のみを残す。
- JSON / CSV のどちらも読める。空入力は `ValueError("empty input")` を送出する。
- 入力ファイルを読んで jsonl に変換・書き出しし、exit code 0 を返す。

| 保証（要約） | 対応テスト |
|---|---|
| バー変換 | `test_convert_rows` |
| 入力読み込み | `test_load_rows_json`, `test_load_rows_csv`, `test_load_rows_empty` |
| end-to-end 変換 | `test_main_end_to_end` |

### 3. `tests/test_config.py` — `bt_dynamic.config`

- `Config.load(path)` は `parameters`・`regime_strategy`・`lot_strategy` を読み、未指定パラメータは `Params()` のデフォルトにフォールバックする。`regime_strategy` / `lot_strategy` のキーは `"a,b"` 形式でセルタプルに変換され、リストに無いセルは単に不在として扱われる。`lot_strategy` を省略すると空 dict（単位ロット）になる。
- config パスは環境変数 `BT_DYNAMIC_CONFIG` でも指定できる。パスも環境変数も無い場合は `FileNotFoundError` を送出する。
- 未知のパラメータキーは `ValueError("unknown parameter")`、不正な `regime_strategy` キー形式は `ValueError("regime_strategy key")`、不正なエントリーモード（`follow`/`flip`/`None` 以外）は `ValueError("regime_strategy value")` をそれぞれ送出する。`lot_strategy` の値は `flat`/`proportional`/`inverse` のみ有効で、それ以外（`None` 含む — セルを外す場合は記載を省略する）は `ValueError("lot_strategy value")` を送出する。
- 構文的に不正な JSON を渡すと `json.JSONDecodeError` を送出する（ラップせず素通しする）。
- `parse_param_overrides` は `"key=value"` のリストを型付き dict に変換する。`=` の無い形式や未知キーはそれぞれ `ValueError("key=value")` / `ValueError("unknown parameter")` を送出する。
- `Config.override(**kwargs)` は元の `Config` を変更せず新しいインスタンスを返す。

| 保証（要約） | 対応テスト |
|---|---|
| 設定読み込み | `test_load_example_config` |
| 設定パス解決 | `test_env_var_fallback`, `test_no_config_path_raises` |
| 入力検証 | `test_unknown_parameter_rejected`, `test_bad_strategy_key_rejected`, `test_bad_entry_mode_rejected` |
| lot_strategy の読み込み | `test_lot_strategy_parsed`, `test_lot_strategy_defaults_empty` |
| lot_strategy の検証 | `test_bad_lot_method_rejected`, `test_null_lot_method_rejected` |
| 不正 JSON の扱い | `test_load_malformed_json_raises` |
| パラメータ上書きのパース | `test_parse_param_overrides` |
| 非破壊な上書き | `test_config_override` |

### 4. `tests/test_data.py` — `bt_dynamic.data`

- `load_jsonl(path)` は `time_utc` 昇順にソートされた `open`/`high`/`low`/`close` 列の DataFrame を返す（入力の順序に依らない）。
- 必須列が欠けている行は `ValueError("missing column")`、空ファイルは `ValueError("no bars")` を送出する。
- 重複タイムスタンプはデデュープされない。安定ソートで元の相対順序を保ったまま両方残る。

| 保証（要約） | 対応テスト |
|---|---|
| バー読み込み | `test_load_jsonl` |
| 入力検証 | `test_load_jsonl_missing_column`, `test_load_jsonl_empty` |
| 重複タイムスタンプ | `test_load_jsonl_duplicate_timestamps_preserved` |

### 5. `tests/test_indicators.py` — `bt_dynamic.indicators`

- `compute_atr` はフラット（値動きなし）な OHLC 系列に対して常に 0 を返す。
- `compute_adx` はトレンドが強いほど高い値を返す（強いトレンド系列 > フラットなノイズ系列）。
- `compute_rsi` は上昇トレンドで 50 超、下降トレンドで 50 未満を返す。
- `compute_atr`/`compute_adx`/`compute_rsi` は、seed 固定のランダムウォーク系列（既知入力）に対して固定の参照値を返す（計算式の互換性を数値レベルで約束する）。

| 保証（要約） | 対応テスト |
|---|---|
| ATR とフラット相場 | `test_compute_atr_zero_for_flat_bars` |
| ADX とトレンド強度 | `test_compute_adx_higher_for_stronger_trend` |
| RSI と方向 | `test_compute_rsi_reflects_direction` |
| 既知入力に対する参照値 | `test_indicator_reference_values` |

### 6. `tests/test_regime.py` — `bt_dynamic.regime`

- `classify(...)` はトレンド強度・ボラティリティ比・方向オシレーターを `(ax1_class, ax2_class, direction)` の3値に分類する。
- 方向の中立帯の境界値ちょうどは中立（`None`）に倒れる。ボラティリティ比の平均が 0 の場合はクラス 1 にフォールバックする。
- 閾値（`ax1_weak`/`vol_hi` 等）は呼び出し側から注入され、同じ入力値でも閾値次第で分類結果が変わる。
- `direction_center` を指定すると中立帯の中心をずらせる（デフォルトは 50）。

| 保証（要約） | 対応テスト |
|---|---|
| 9セル分類 | `test_classify_all_levels` |
| 境界条件 | `test_classify_band_edges` |
| 閾値の外部注入 | `test_classify_injected_thresholds` |
| 方向中心のカスタマイズ | `test_classify_custom_direction_center` |

### 7. `tests/test_engine.py` — `bt_dynamic.engine`

- `calc_result_pips(direction, entry, exit, pip)` は BUY/SELL の方向に応じた符号付き pips を返す。
- `resolve_entry(price, mode, bias, params)` は `follow` でバイアス方向のまま、`flip` で逆方向のポジションを組み、TP/SL を price ± pips で計算する。`mode` または `bias` が `None` なら `None` を返す。
- `run_day(df, date, config)` はトレードのリストを返す。各トレードは `exit ∈ {TP, SL, EOD}`・`direction ∈ {BUY, SELL}`・`exit_time > entry_time` を満たし、単一ポジションモード（同日内のトレードは重複しない）で走る。TP 決済の `result_pips` は `tp_pips - commission_pips` に一致する。
- `regime_strategy` に無いセルは flat（トレード無し）として扱われる。
- ウォームアップに十分なバー数が無い日はトレード無しで空リストを返す。
- `debug_day(df, date, config)` は判定ごとのレコードを返し、各レコードの `action` は `ENTRY...` または `skip(...)` で始まる。`ENTRY` レコードは `ax1`/`vol_ratio`/`direction_val`/`ax1_class`/`ax2_class` を含む。`follow` セルは `action` がバイアス方向と一致し、`flip` セルは逆方向になる。
- `run_day(..., use_dynamic=True, lookback_days=N)` はエラーなく走る。
- `--dynamic`（`use_dynamic=True`）の閾値は静的な config 値ではなく、直近 `lookback_days` 営業日のデータ分布（パーセンタイル）から実際に導出される。トレンド強度が日によって変動するデータでは、静的閾値と動的閾値でトレードの `regime` 分類（`ax1_class`）が異なる。
- `summarize_dict(trades)` は空リストに `{"trades": 0}` を返し、非空リストには `trades`/`wins`/`losses`/`win_rate`/`total_pips`/`avg_pips`/`best_pips`/`worst_pips` と `by_exit`/`by_cell_mode`/`by_regime` の内訳を返す。

| 保証（要約） | 対応テスト |
|---|---|
| pips 計算 | `test_calc_result_pips` |
| エントリー解決 | `test_resolve_entry_follow_and_flip` |
| 日次バックテスト | `test_run_day_produces_trades` |
| 未定義セルの扱い | `test_run_day_unlisted_cell_stays_flat` |
| ウォームアップ不足 | `test_run_day_insufficient_data` |
| デバッグレコード | `test_debug_day_records`, `test_debug_day_flip_shows_actual_direction` |
| 動的閾値モード（smoke） | `test_run_day_dynamic_thresholds` |
| 動的閾値がデータ由来であること | `test_run_day_dynamic_thresholds_differ_from_static` |
| 成績集計（`summarize_dict`） | `test_summarize_dict_empty`, `test_summarize_dict_aggregates` |

### 8. `tests/test_selection.py` — `bt_dynamic.selection`

- `business_days(start, n)` は `start` から週末を飛ばして `n` 営業日を返す。
- `season_range(year, season)` は季節窓の開始日（土日なら翌営業日にずらす）と営業日数を返す。未知の季節名は `ValueError("unknown season")` を送出する。
- `daily_axis_mean(df, target, compute_axis)` は前営業日をウォームアップに使って対象日の軸平均を返し、データの無い日は NaN を返す。
- `rank_dates(df, dates, compute_axis)` は軸の日次平均の降順で日付を返し、データの無い日（NaN）は結果から落とす。
- `sample_dates(dates, n, seed)` は同じ seed で同じ結果を返し、`n` が母数を超える場合は全件を返す。

| 保証（要約） | 対応テスト |
|---|---|
| 営業日生成 | `test_business_days_skips_weekends` |
| 季節窓 | `test_season_range_starts_on_business_day`, `test_unknown_season_rejected` |
| 日次軸平均 | `test_daily_axis_mean`, `test_daily_axis_mean_missing_day_is_nan` |
| ランキング | `test_rank_dates_descending_and_drops_missing` |
| サンプリング | `test_sample_dates_reproducible_and_capped` |

### 9. `tests/test_sizing.py` — `bt_dynamic.sizing`

- `lot_table(trades)` は `flat`/`proportional`/`inverse` の3方式のロットを返し、各方式は平均 1 に正規化される。`proportional` は `ax1` に対して増加、`inverse` は減少、`flat` は常に 1。
- `apply_lot_strategy(trades, lot_strategy)` は各トレードに `lot` と `sized_pips`（`result_pips × lot`）を付与した新しいリストを返し、入力の trades は変更しない。空リストには空リストを返す。
- trades に現れるセルが `lot_strategy` に無い場合は `ValueError("missing cell")` を送出する（デフォルトに倒さない）。

| 保証（要約） | 対応テスト |
|---|---|
| ロット計算と正規化 | `test_lot_table_normalized_to_mean_one`, `test_lot_table_orderings` |
| サイズ適用 | `test_apply_lot_strategy_sizes_pips`, `test_apply_lot_strategy_empty_trades` |
| 未定義セルの拒否 | `test_apply_lot_strategy_missing_cell_rejected` |

## About

対象は pip パッケージ `bt-dynamic`（`bt_dynamic`）の公開 API と、コンソールスクリプト `bt-dynamic` / `bt-dynamic-convert` の外部から観測可能な振る舞い。対象外はアンダースコア始まりの関数・CLI 内部ヘルパー。**ここに載っていない振る舞いは約束ではなく、予告なく変わりうる。** 地位は [design-decisions.md](design-decisions.md) と同格。
