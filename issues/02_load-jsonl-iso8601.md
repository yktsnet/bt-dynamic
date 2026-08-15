## `load_jsonl` が混在した ISO8601 形式を読めない
id: 02
branch-slug: load-jsonl-iso8601
github_issue:
status: open
type: fix
対象: src/bt_dynamic/data.py, tests/test_data.py, docs/guarantees.md
内容: 1つの JSONL 内で `time_utc` の表記が揺れていると `load_jsonl` が `ValueError` で落ちる。どちらも妥当な ISO8601 だが、pandas が先頭行から形式を推定して以降を同じ形式として解釈するため。バーの生成元が複数あると（例: 一括エクスポートした過去分と、後から日次で追記した分）容易に起きる。実データで実際に踏んだ。
確認: `PYTHONPATH=src pytest -q`

---

### 保証
- 新たに宣言する保証:
  - `load_jsonl` は 1ファイル内で `time_utc` の表記が揺れていても（秒の小数部の有無・タイムゾーン指定子の有無など、いずれも妥当な ISO8601 である限り）行ごとに解釈して読み込む。
- 維持する保証（`docs/guarantees.md` の 4. `tests/test_data.py`）:
  - `time_utc` 昇順にソートされた `open`/`high`/`low`/`close` 列の DataFrame を返す（入力の順序に依らない）。
  - 必須列が欠けている行は `ValueError("missing column")`、空ファイルは `ValueError("no bars")` を送出する。
  - 重複タイムスタンプはデデュープされない。安定ソートで元の相対順序を保ったまま両方残る。
  - ISO8601 として解釈できない文字列は引き続きエラーになる（何でも受け入れるようにはしない）。

台帳 `docs/guarantees.md` のセクション 4 に、混在形式を読める旨の1行と対応テストを追加する。

---

### 再現

同一ファイル内に以下の2行がある状態で `load_jsonl` を呼ぶと落ちる。

```
{"time_utc": "2026-01-01T18:00:00.000000Z", ...}
{"time_utc": "2026-07-26T21:00:00Z", ...}
```

```
ValueError: time data "2026-07-26T21:00:00Z" doesn't match format "%Y-%m-%dT%H:%M:%S.%f%z"
```

### src/bt_dynamic/data.py

`load_jsonl` の `pd.to_datetime(df["time_utc"])` が形式を暗黙に推定している箇所（31行目付近）。pandas が案内しているとおり `format="ISO8601"` を明示すれば、行ごとに ISO8601 として解釈される。`format="mixed"` は ISO8601 以外も推測しにいくため採らない（不正な入力を黙って通す方向に倒れる）。

docstring の非自明な制約として、なぜ形式を明示するのかを1行残すこと（推定に任せると先頭行の形式に引きずられる、という理由）。

### tests/test_data.py

同一ファイル内に小数秒ありの行と無しの行を混ぜた JSONL を読み、両方の行が正しい時刻としてソート済みで返ることを検証する。あわせて、ISO8601 として解釈できない文字列（例: `"not a time"`）が引き続きエラーになることも確認する。
