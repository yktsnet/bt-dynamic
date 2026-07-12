# PLAN — bt-dynamic

「動的レジーム切替」という単一仮説を、データ取得 → 9セル分類 → follow/flip 判定 → 比較検証まで通して実装した FX バックテスト研究リポジトリ。

汎用バックテストエンジン（backtesting.py 等）が「何でも書ける土台」であるのに対し、本リポは一つの問いに端から端まで答えた**研究の完結性**を見せることを目的とする。

名前は配布名・リポ名とも `bt-dynamic`、import 名 `bt_dynamic` に統一する（PyPI で未登録を確認済み）。

## 配布 — pip（PyPI）

リポは二層。汎用コア（エンジン + デフォルト指標 + CLI）は **PyPI 配布の組み込み型**、研究ナラティブ + `examples/trend/` は **clone で読む研究型**。

pip 配布の根拠は「組み込み利用者がすでに存在する」こと。`ops_dynamic` が本番でこのコアを組み込んでおり（現状は PYTHONPATH 参照）、pip 化でバージョン固定の依存に置き換えられる。ポートフォリオ目的ではなく実運用の要請として module-guide の「組み込み型 → レジストリ配布必須」に該当する。

wheel に入るのは汎用エンジンと中立デフォルトのみ。`REGIME_STRATEGY` の本番対応表・実パラメータは設定 JSON として利用者（＝本番側）が注入するため、「答えはパッケージにそもそも存在しない」ことが配布形式で証明される。

## 仮説

静的バックテスト（過去成績で戦略を固定する）は、相場環境が変われば共倒れする。
相場を短い時間窓で継続的に分類し、局面に応じて戦略を**動的に切り替える**ことでこれに対抗する。

## 設計の柱

- **汎用性とシンプルさの両立** — コア（バックテストエンジン）は触らず、戦略・指標を差し替え可能に保つ。
- **設定ファイル（JSON）による外部注入** — 閾値・TP/SL・9セル対応表（REGIME_STRATEGY）をすべて設定JSONに集約し、CLI引数や環境変数でファイルパスを指定して外部注入する。本番のエッジはコードに焼き込まず**構造的に分離**する（「伏せている」のではなく「リポ外にある」）。

## 9セルの枠組み（公開する思考）

- 3指標を3段階（0/1/2）に分類し、2軸の組み合わせで9セルを構成。
- 3軸目（方向指標）が BUY / SELL / None を返す。
- 各セルに follow（順張り）／ flip（逆張り）／ None（ノーポジ）を割り当てる。

## 公開 / 非公開の線 — 「問いと手法は出す、答えは出さない」

枠組み（9セル・動的閾値・ADX/ATR/RSI）はクオンツの一般概念でありエッジではない。エッジは「どの局面で順張り/逆張りが効くか」という**答え**＝ `REGIME_STRATEGY` の対応表の中身・閾値の実数・成績・通貨ペア。

| | 内容 |
|---|---|
| **問い（出す）** | なぜ動的レジーム切替か（静的BTの共倒れ回避）|
| **手法（出す）** | 9セル分類・follow/flip・比較で仮説を潰す作法（`compare_*`）・研究/本番の分離・設定ファイル(JSON)設計 |
| **答え（出さない）** | `REGIME_STRATEGY` の本番値・閾値の実数・TP/SL・成績・通貨ペア |

配るのはデータ取得コード・配管・設定JSONの**中立 or 説明用ダミー**のパラメータと対応表。
配らないのは本番パラメータと**本番の対応表**（どちらも JSON/環境変数で外部注入＝リポ外）、データセットの塊。

> 注意：`REGIME_STRATEGY` の対応表は中立パラメータでも「形」が答えを示唆する。パラメータだけでなく**対応表自体も外部注入**にし、リポには中立／説明用ダミーのみ置く。

## 戦略スコープ — trend/ 1本に絞る

戦略を増やさない。「単一仮説を端から端まで」というナラティブが本リポの強み。戦略を足すと「色々試す人」に戻り、エッジ形状のヒントも保守コストも増える。1本をクリーンに見せる。

## ディレクトリ構造 — 「汎用と固有の分離」

[module-guide.md](file:///Users/ykts/dotfiles/docs-agents/module-guide.md) の設計規範に則り、汎用バックテストコアと、ドメイン適用例のサンプル戦略をディレクトリレベルで分離します。

```
bt-dynamic/
├── pyproject.toml                   # pip 配布定義 (console script: bt-dynamic)
├── src/
│   └── bt_dynamic/                  # 汎用バックテストパッケージ (エッジなし・戦略を import しない)
│       ├── config.py                # Config.load(path) — パラメータ + 対応表の外部注入
│       ├── regime.py                # classify() — 純関数・閾値は引数
│       ├── indicators.py            # デフォルト指標 (ADX/ATR/RSI) + 差し替え用 IndicatorSet
│       ├── engine.py                # run_day() / summarize() — 定数グローバルなし
│       ├── data.py                  # JSONL ローダ
│       └── cli.py                   # bt-dynamic コマンド
├── examples/
│   └── trend/                       # トレンドフォロー適用例 (教科書的ダミー値のみ)
│       ├── config.json              # 説明用ダミー設定 (本番と別物)
│       ├── data/sample_m5.jsonl     # 合成データ (乱数ウォーク・実データなし)
│       ├── generate_data.py         # 合成データの再生成スクリプト
│       ├── demo.tape                # VHS 台本
│       └── README.md                # サンプルの実行手順説明
├── tests/                           # src をミラー配置
└── README.md                        # リポジトリ全体の紹介
```

移植時の構造修正（dotfiles 版からの差分）:
- コアが `trend.rules` を import していた逆向き依存を解消し、対応表は Config 経由で注入する。
- import 時のグローバル設定ロードを廃し、明示的な `Config.load(path)` にする。
- CLI がモジュール定数を書き換える方式を廃し、`run_day()` にパラメータを引数で渡す。
- 設定キーは指標非依存の一般名（`ax1_weak` / `vol_lo` / `direction_band`）とし、ADX/ATR/RSI は「デフォルト指標」の位置づけに落とす。

## MVP 完成条件 (DoD)

1. `pip install -e .` 後、`bt-dynamic --config examples/trend/config.json --data examples/trend/data/sample_m5.jsonl` でエラーなくバックテストが走り、成績サマリーが CLI に出力されること。
2. `vhs examples/trend/demo.tape` で 30秒の動作実演 GIF が正常に生成できること。
3. `tests/` 配下の pytest がすべてパスすること。

## 文章化（README / Zenn）— ここが本体

配管コードではなく**思考**が本リポの価値。汎用インジケーターのコードだけでは埋もれる。文章で「なぜ動的切替か／どう仮説を潰したか」を語って初めて汎用エンジンとの差（完結性）が立つ。

- README は readme-guide に従い、Design Decisions に JUDGE.md を統合する。
- Zenn 記事は課題→着想→検証作法→設計を語る。**成績の実数・対応表の中身・どのセルが効いたかという結論は書かない**。
- 「答えは構造的に分離してある（外部注入）」と書けること自体が設計力の証明になる。

## データ

利用者が API で自取得する。リポにデータは同梱せず、取得手順のみ置く。
- 主: Dukascopy（key 不要・完全無料、OSS ダウンローダあり）
- 従: Alpha Vantage（公式無料 API、利用者が自分の key を投入）
- yfinance は動作確認用オプションに留める（Yahoo 規約がグレー）

各ソースの規約に従い、データ再配布はしない。提示（VHS で数行映す等）は de minimis として許容。

## Demo（VHS）

実データの一スライス × 中立パラメータで「**仕組みと検証作法**」を実演する。
- 撮る候補: 1日の判定が9セルのどこに落ちるか／動的 vs 静的の比較／9セル分類の瞬間
- 出典（ソース・日付・足）を画面に明記する。
- **成績は実績として語らない**（中立パラメータ × 無料1h足は本番と無関係）。

## TODO

- [ ] Dotfiles（先行リファクタリング済み）から `src/bt_dynamic/` へのコア移植
  - [ ] engine.py / regime.py / config.py / indicators.py / data.py の配置（依存逆転の解消込み）
  - [ ] pyproject.toml（hatchling・console script `bt-dynamic`）
  - [ ] argparse による CLI（cli.py）
- [ ] 適用例 `examples/trend/` の構築
  - [ ] 説明用ダミー設定 config.json（教科書的対応表・本番と別物）
  - [ ] 合成データ data/sample_m5.jsonl + generate_data.py（実データは同梱しない）
  - [ ] examples/trend/README.md
- [ ] 自動テスト `tests/`
  - [ ] test_config.py（ロード・検証・不正キー拒否）
  - [ ] test_regime.py（9セル分類・閾値注入）
  - [ ] test_engine.py（run_day 実行フロー・exit 判定）
- [ ] デモ（VHS）および README
  - [ ] examples/trend/demo.tape の作成と demo.gif の生成
  - [ ] README.md の本格化（repo-readme・JUDGE.md 統合）と英語版（readme-i18n）
- [ ] PyPI 公開（リポ公開 = repo-publish 後）
- [ ] ops_dynamic の参照を PYTHONPATH から pip 依存へ切り替え（別リポ作業）

注: dotfiles 版の比較スクリプト群（compare_dynamic / compare_lot / compare_regimes / analyze）は MVP に含めない。「比較で仮説を潰す作法」は README/Zenn で語り、コードの移植は利用ニーズが立ってから判断する。
