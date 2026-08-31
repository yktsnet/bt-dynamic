## PR記録: feat: 候補間の差を日次で対応させて評価する
issue: 04 (04_paired-candidate-diff.md)
PR: https://github.com/yktsnet/bt-dynamic/pull/12
Merged: f8c3d1c138afbc81a695f87a7b9c9ac579e95c80

## 変更内容
2つの設定を同一期間で走らせ、日ごとに対応させた損益差の平均と信頼区間を返す
`paired_diff(bars, dates, baseline, candidate)` を `validation.py` に追加した。
統計量そのものは `engine.dispersion` を日次差分の Series にそのまま適用して求め、
実装を二重に持たない。`param_sweep` の各候補にも `diff_vs_base` を持たせ、基準
設定（上書き無しの候補）に対する同じ日次差分統計を、既に持っている `trades` から
計算する（バックテストの再実行はしない）。

対応の索引は与えられた `dates` そのもので、片方（または両方）がトレードしなかった
日は 0.0 として数える。トレードのあった日だけを拾うと対応が崩れて偏るため。

## 保証
- 2つの設定を同一の日付集合で評価し、日ごとに対応させた損益差の平均・標準誤差・
  t統計量・95%信頼区間を返す
  → `test_paired_diff_returns_expected_keys_and_day_count`
- 対応の索引は与えられた日付集合そのものであり、片方（または両方）がトレードしな
  かった日は 0.0 として数える
  → `test_paired_diff_pairs_by_day_and_fills_untraded_days_with_zero`
- 差の統計量は、両者を独立に評価した統計量から計算した値とは一致しない
  → `test_paired_diff_does_not_match_naive_independent_combination`
- `param_sweep` の各要素が、基準設定に対する差の統計量を持つ。基準設定自身の差は
  ゼロになる
  → `test_param_sweep_carries_diff_vs_base_computed_from_existing_trades`
- 差の計算はその場で済ませ、バックテストを走らせ直さない
  → `test_param_sweep_computes_diff_without_rerunning_the_backtest`（`run_period`
  呼び出し回数を監視し、候補数と一致することを確認）
- 維持する保証（`param_sweep` の t統計量降順・`overrides`/`summary`/`trades` の
  保持、`run_period`/`split_train_test` の既存挙動、検証層の純関数性）は既存
  テストのままカバーされ、退行なし
- `docs/guarantees.md` §10 を更新: `param_sweep` の戻り値に `diff_vs_base` を
  追記し、新規 `paired_diff` の保証項目とテスト対応表を追加

## 静的確認結果
- `git diff --name-only --cached` は issue の対象と完全一致:
  `CHANGELOG.md`, `docs/guarantees.md`, `src/bt_dynamic/validation.py`,
  `tests/test_validation.py`
- `paired_diff`/`_paired_diff_stats`/`_daily_pips` の呼び出し元（`param_sweep`
  内の追加ループ、テスト側の import）を確認。`engine.dispersion` の import 追加
  も含めて caller/import の整合性を確認した
- `context/conventions.md` に沿って `from __future__ import annotations` は
  既存のまま、型ヒントは PEP604 スタイル、純関数（引数外の状態に依存しない）
- `context/structure.md` の一方向依存を維持: 新関数は `validation.py` に置き、
  `engine`/`config` のみを import する

## 検証手順
`nix-shell -p "python3.withPackages(ps: with ps; [pandas numpy pytest])" --run "PYTHONPATH=src pytest tests -q"` → 91 passed



## feat: 候補間の差を日次で対応させて評価する
id: 04
branch-slug: paired-candidate-diff
github_issue: 13
status: close
type: feat
対象: src/bt_dynamic/validation.py, tests/test_validation.py, docs/guarantees.md, CHANGELOG.md
内容: 2つの設定を同一期間で走らせ、日ごとに対応させた損益差の平均と信頼区間を返す関数を足す。`param_sweep` の各候補にも基準設定との差を持たせる。
確認: `nix-shell -p "python3.withPackages(ps: with ps; [pandas numpy pytest])" --run "PYTHONPATH=src pytest tests -q"` が通ること。

---

### 保証

- 新たに宣言する保証
  - 2つの設定を同一の日付集合で評価し、**日ごとに対応させた損益差**の平均・標準誤差・
    t統計量・95%信頼区間を返す
  - 対応の索引は与えられた日付集合そのものであり、片方（または両方）がトレードしなかった
    日は 0.0 として数える。トレードのあった日だけを拾うと対応が崩れて偏るため
  - 差の統計量は、両者を独立に評価した統計量から計算した値とは一致しない（相関ぶん
    分散が小さくなる）。これが本関数の存在理由である
  - `param_sweep` の各要素が、基準設定（上書き無しの候補）に対する差の統計量を持つ。
    基準設定自身の差はゼロになる
- 維持する保証（`docs/guarantees.md` §10 より）
  - `param_sweep` は t統計量の降順に並び、各要素は `overrides` / `summary` / `trades` を持ち、
    上書き無しの元 config を必ず含む
  - `run_period` はデータの無い日を黙って飛ばす。`split_train_test` は時系列順を保つ
  - 検証層はすべて純関数で、渡された `Config` と `bars` を変更しない
- 台帳の変更: §10 に新関数と `param_sweep` の戻り値追加を書き足すため `docs/guarantees.md` を対象に含める

---

### なぜ

現状 `param_sweep` は各候補を独立に評価している。しかし候補どうしは**同じ日付集合**の
上で走っており、市場のノイズは共通である。差を直接見れば共通成分が相殺され、絶対量を
測るより検定力が上がる。データを増やさずに解像度だけを上げられる。

実例。priv 側の全期間検証で、現行値は平均 +0.12 pips/trade・CI [-0.82, +1.07]、
tp60/sl25 は +1.29・CI [-0.35, +2.94] だった。どちらの区間もゼロを跨ぐため、
独立に見るかぎり「差があるとは言えない」で止まる。両者は同じ1471日の上を走っているので、
差を直接測ればもっと狭い区間が出るはずである。

### 要件

1. **対応の単位は日であって、トレードではない。** 設定が違えば決済時刻が変わり、
   単一ポジションモードではその後の建玉機会も変わるため、トレードは1対1に対応しない。
   日次に集計すれば両者に共通の索引が取れる
2. **トレードの無い日を 0.0 として含める。** 片方だけがトレードした日を落とすと、
   「トレードした日だけ」という条件付けが入って偏る
3. **再実行しない。** `param_sweep` は既に各候補の `trades` を持っている。差の計算は
   その場で済ませ、バックテストを走らせ直さない
4. **区間は正規近似**（`engine.dispersion` と同じ z=1.96）。日数が2未満、分散ゼロの
   場合は `None` を返す（`dispersion` と同じ規約に揃える）

### 設計の指し先

- 差の統計量そのものは `engine.dispersion` がそのまま使える。日次差の Series を作って
  渡せばよく、統計の実装を二重に持たない
- 新関数の置き場は `validation.py`。`engine` は単日のバックテストに閉じており、
  複数設定の比較は検証層の責務（`context/structure.md` の一方向依存）

### やらないこと

- 多重比較の補正。何通り比べたかは呼び出し側の文脈であり、パッケージは知らない
- 並び順の変更。`param_sweep` は t統計量の降順のまま
