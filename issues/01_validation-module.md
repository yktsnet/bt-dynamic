## 検証モジュール（train/test 分割・セル寄与分解・パラメータグリッド）を追加する
id: 01
branch-slug: validation-module
github_issue:
status: open
type: feat
対象: src/bt_dynamic/validation.py (新規), tests/test_validation.py (新規), docs/guarantees.md, context/structure.md
内容: 設定の良し悪しを「全期間の合計 pips」だけで判断すると過学習を検出できない。過去に、非連続・少数サンプルの季節窓で正だったセルが、連続フルヒストリーでは負・直近3年連続負だった実例がある。この種の検証（複数年を連続で流す・時系列 train/test 分割・セル単独での寄与分解・パラメータグリッド内での現行値の順位）は毎回その場限りのスクリプトで書かれ、使い捨てられてきた。これをパッケージの常設 API にして、検証手順を再現可能にする。
確認: `PYTHONPATH=src pytest -q`

---

### 保証
- 新たに宣言する保証:
  - `run_period(bars, dates, config)` は複数日・複数年にまたがるバーとその期間の営業日リストを受け取り、日ごとの `run_day` 結果を時系列順に連結したトレードのリストを返す。データが存在しない日は黙って飛ばし、例外を送出しない。`multi_position` 引数は `run_day` にそのまま渡る。
  - `split_train_test(dates, ratio)` は日付リストを時系列順のまま前後2つに分割する。シャッフル・ランダム抽出は行わない（時系列の順序が検証の前提であるため）。`ratio` は train 側の割合で、0 または 1 に潰れる分割は `ValueError` を送出する。
  - `cell_breakdown(bars, dates, config)` は、config の `regime_strategy` に載っている各セルについて「そのセルだけを有効にした config」で個別にバックテストし、セルごとの成績（`summarize_dict` 形式）を返す。**セル単独の成績の合計は、全セルを同時に有効にした成績と一致しない**（単一ポジションモードではセル同士がポジションを奪い合うため）。この非加算性は仕様であり、両方を別々に観測できることがこの関数の目的である。
  - `param_sweep(bars, dates, config, overrides)` は `Config.override(**kwargs)` で作った各設定を同一期間で評価し、合計 pips の降順に並べた結果を返す。各要素は「与えた上書き内容」と「成績」を持つ。上書き無しの元 config も必ず結果に含まれ、グリッド内での順位が読み取れる。
  - 上記すべては純関数であり、渡された `Config` と `bars` を変更しない。ファイル I/O を行わず、設定を暗黙に読まない。
- 維持する保証（`docs/guarantees.md` より）:
  - 7. `engine.run_day` / `summarize_dict` の既存の振る舞い（トレードの形式・未定義セルは flat・ウォームアップ不足は空リスト・集計キー）。本 Issue はこれらを呼び出すだけで変更しない。
  - 8. `selection` の営業日生成・季節窓・ランキング・サンプリング。分割・期間指定は既存の営業日概念に乗せる。
  - 9. `sizing` の事後ロット計算。本 Issue はロットに関与しない（`result_pips` ベースで評価する）。
  - 3. `Config` が frozen であり `override` が非破壊であること。

台帳 `docs/guarantees.md` に新セクション「10. `tests/test_validation.py` — `bt_dynamic.validation`」を追加する。

---

### src/bt_dynamic/validation.py（新規）

`engine` の上に乗る評価層。`regime` / `engine` / `config` を import してよいが、逆向きの依存を作らない（既存モジュールから `validation` を import しない）。

公開するのは以下4つ。名前は変えてよいが、責務は分けたまま保つこと。

- **`run_period`** — 期間を跨いだ実行。呼び出し側が複数年の JSONL を連結して1つの DataFrame として渡す前提にする（年ごとに DataFrame を分けて持つ構造にはしない。年境界を跨ぐウォームアップが取れなくなるため）。
- **`split_train_test`** — 時系列分割。ランダム抽出を提供しない。
- **`cell_breakdown`** — セル単独評価。「そのセルだけ有効な config」は `dataclasses.replace` で `regime_strategy` を差し替えて作る（既存の `Config` は変更しない）。priv 側の同等処理が `compare_lot.py` の `filter_cells` にあるので、責務が重なるならそちらを将来こちらへ寄せられる形にしておく。
- **`param_sweep`** — グリッド評価。グリッドの中身（どの値を振るか）は呼び出し側が組み立てて渡す。`tp_pips` 等の具体的なパラメータ名をこのモジュールにハードコードしない（エッジを持ち込まないため）。

年別・レジーム別の内訳は既存の `summarize_dict` の `by_regime` / `by_cell_mode` で取れるものは再実装しない。年別集計だけは既存に無いが、本 Issue の対象外とする（呼び出し側が日付でグループ化して `run_period` を複数回呼べば足りるため）。

### tests/test_validation.py（新規）

`tests/` は `src/` に1対1対応する規約。既存テストと同じく合成データで書く（`examples/trend/data/sample_m5.jsonl` または `pytest` 内で生成した乱数ウォーク）。実データ・本番値を持ち込まない。

上の保証節の各項目に対応するテストを置く。特に以下は明示的に検証する。

- `split_train_test` が時系列順を保つこと、および潰れる `ratio` を拒否すること
- `cell_breakdown` の各セル成績の合計が、全セル同時実行の成績と**一致しない**ケースが存在すること（非加算性が仕様であることをテストで固定する）
- `param_sweep` の結果に元 config が含まれ、降順に並んでいること
- 入力の `Config` と DataFrame が呼び出し後に変更されていないこと

### context/structure.md

`src/bt_dynamic/` のツリーに `validation.py` の行を追加し、「データフロー」図の `summarize()` の後段に評価層として位置づけを1行足す。
