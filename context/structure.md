# Structure

```
bt-dynamic/
├── pyproject.toml              # pip 配布定義。console scripts: bt-dynamic / bt-dynamic-convert
├── src/bt_dynamic/             # 汎用バックテストパッケージ（エッジなし・戦略を import しない）
│   ├── config.py                 # Config / Params（frozen dataclass）。Config.load(path) が唯一の入口
│   ├── data.py                    # JSONL bar ローダ（time_utc/open/high/low/close）
│   ├── indicators.py              # IndicatorSet（ax1/ax2/direction を計算する関数の束）＋ default ADX/ATR/RSI
│   ├── regime.py                  # classify() — 9セル分類の純関数
│   ├── engine.py                  # run_day() / debug_day() / summarize() / summarize_dict()
│   ├── selection.py               # バックテスト対象日の選定（営業日・季節窓・軸値ランキング・サンプリング）
│   ├── sizing.py                  # 事後ロット計算（flat/proportional/inverse、Config.lot_strategy で注入）
│   ├── convert.py                 # bt-dynamic-convert（dukascopy-node 出力 → JSONL 変換）
│   └── cli.py                     # bt-dynamic コマンド本体（argparse）
├── examples/trend/             # トレンドフォロー適用例。中立・教科書的ダミー値のみ
│   ├── config.json                # 説明用ダミー設定
│   ├── data/sample_m5.jsonl       # 合成データ（乱数ウォーク・実データではない）
│   ├── generate_data.py           # 合成データの再生成
│   └── demo.tape / demo.gif       # VHS デモ
├── docs/fetch-data.md          # 実データ取得手順（Dukascopy 主・Alpha Vantage 従）
└── tests/                      # src をミラー配置（test_config.py 等）
```

## データフロー

```
JSONL bars ──data.load_jsonl──▶ DataFrame(time-indexed OHLC)
                                        │
                        indicators.IndicatorSet (ax1/ax2/direction 計算)
                                        │
                         regime.classify() で決定ポイントごとに9セル分類
                                        │
                    engine.run_day() が Config.regime_strategy を引いて
                    follow/flip/flat を決定し、TP/SL ブラケットで日次バックテスト
                                        │
                     engine.summarize() / summarize_dict() で成績集計
```

`cli.py` が上記を配線する層。`Config.load()` で対応表・閾値を外部注入し、`--indicators` / `--param` で指標・パラメータを差し替え可能にする。`src/bt_dynamic/` はこのフロー全体で `examples/` や本番側リポを import しない一方向依存。
