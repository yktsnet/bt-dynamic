# Conventions

- 全モジュール冒頭に `from __future__ import annotations`。型ヒントは `str | None` 等 PEP 604 スタイル（Python 3.10+ 前提）。
- `Params` / `Config` は `@dataclass(frozen=True)`。変更は `dataclasses.replace()` で新インスタンスを作る（ミュータブルな共有状態を持たない）。
- コアのロジック関数（`regime.classify`・`engine.resolve_entry`・`engine.calc_result_pips` 等）は純関数。閾値・パラメータは引数で渡し、モジュールレベルの定数やグローバル状態に依存しない。
- 設定は `Config.load(path)` の明示呼び出しでのみ読む。import 時の暗黙ロードをしない（本番値をパッケージ・リポの外に保つための不変条件。`CLAUDE.md` 参照）。
- `src/bt_dynamic/` はドメイン非依存の抽象名を使う（`ax1` = トレンド強度, `ax2` = ボラティリティ, `direction` = 方向オシレーター）。ADX/ATR/RSI 等の具体指標名は `indicators.py` の default 実装にのみ現れ、`engine.py`・`regime.py` からは見えない。
- 指標・戦略の差し替えは `IndicatorSet`（dataclass にまとめた関数群）を渡す形で行う。CLI からは `--indicators file.py` で `INDICATORS = IndicatorSet(...)` を定義したファイルを注入する。
- エラーは `ValueError` / `FileNotFoundError` を送出元の情報（ファイルパス・不正なキー）付きで送出する。例外を握りつぶさない。
- クラスは状態を持つ値（`Config` / `Params` / `IndicatorSet`）にのみ使う。ステートレスな処理は関数として `config.py` / `data.py` / `indicators.py` / `regime.py` / `engine.py` / `cli.py` に責務ごとに分ける。
- docstring はモジュール冒頭に設計意図（非自明な制約）を書く。関数レベルは非自明な場合のみ（例: `debug_day` が「ポジション状態を無視した分類器ビュー」であること）。
- テストは `tests/test_{module}.py` が `src/bt_dynamic/{module}.py` に1対1対応する。pytest、浮動小数比較は `pytest.approx`。
