# bt-dynamic

動的レジーム切替のバックテストエンジン。相場を短い時間窓で 9 セル（トレンド強度 × ボラティリティ、各 3 段階）に分類し、セルごとに順張り（follow）/ 逆張り（flip）/ ノーポジ（None）を切り替える単一仮説を、分類 → 判定 → 検証まで通して実装する。

静的バックテスト（過去成績で戦略を固定する）は相場環境が変われば共倒れする——この問いへの対抗が動的レジーム切替であり、本リポはその検証の枠組みと作法を公開する。**セル対応表の本番値・閾値の実数・成績・通貨ペアは公開しない**。それらはすべて設定 JSON の外部注入であり、パッケージにもリポにもそもそも存在しない。

![demo](examples/trend/demo.gif)

（デモは合成データ × 説明用ダミー設定。`nix-shell -p vhs jq "python3.withPackages(ps: with ps; [pandas numpy])" --run 'vhs examples/trend/demo.tape'` で再生成できる）

## インストール

```bash
pip install bt-dynamic
```

## 使い方

標準の使い方は実データを自分で取得して回すこと（リポにデータは同梱しない。取得手順は [docs/fetch-data.md](docs/fetch-data.md)）。

```bash
# 1h 足を取得（API key 不要）して変換
npx dukascopy-node -i eurusd -from 2025-01-01 -to 2025-03-31 -t h1 -f json
bt-dynamic-convert download/eurusd-h1-*.json -o bars.jsonl

# バックテスト
bt-dynamic --config my-config.json --data bars.jsonl
```

まず動きを見るだけなら同梱の合成サンプルで:

```bash
bt-dynamic --config examples/trend/config.json --data examples/trend/data/sample_m5.jsonl
```

- `--config`: パラメータとセル対応表（`regime_strategy`）を持つ JSON。`$BT_DYNAMIC_CONFIG` でも指定可
- `--data`: JSONL のバーデータ（`time_utc` / `open` / `high` / `low` / `close`）
- `--dynamic`: 閾値を固定値でなく直近営業日のパーセンタイルから動的に導出する

## 差し替えながら回す

このツールの本体は「インジケーターとパラメータを差し替えて、結果を見て、また回す」ループ。

**パラメータ**は JSON を編集せず引数で上書きできる:

```bash
bt-dynamic --config c.json --data bars.jsonl --param tp_pips=15 --param ax1_weak=20
```

**インジケーター**は `IndicatorSet` を公開する Python ファイルを渡して差し替える:

```bash
bt-dynamic --config c.json --data bars.jsonl --indicators my_strategy/indicators.py
```

```python
# my_strategy/indicators.py
from bt_dynamic import IndicatorSet

INDICATORS = IndicatorSet(
    compute_ax1=my_trend_strength,   # 軸1: トレンド強度
    compute_ax2=my_volatility,       # 軸2: ボラティリティ
    compute_direction=my_oscillator, # 方向バイアス（中心値付き振動子）
)
```

**結果の比較**は `--json` で機械可読サマリーを吐き、好きに並べる:

```bash
bt-dynamic --config c.json --data bars.jsonl --param tp_pips=15 --json >> runs.jsonl
bt-dynamic --config c.json --data bars.jsonl --param tp_pips=30 --json >> runs.jsonl
jq '{tp: .meta.param_overrides.tp_pips, total: .summary.total_pips}' runs.jsonl
```

## 戦略を増やすには

1戦略 = 1ディレクトリ。`examples/trend/` をコピーして中身を差し替えるのが増やし方の標準形。

```
my_strategies/
  breakout/
    config.json     # このセル対応表・閾値
    indicators.py   # INDICATORS = IndicatorSet(...)（デフォルト指標のままなら不要）
  meanrev/
    config.json
```

```bash
bt-dynamic --config my_strategies/breakout/config.json --indicators my_strategies/breakout/indicators.py --data bars.jsonl
```

エンジン（この package）は触らない。戦略の中身はあなたのファイルにだけ存在する。

## Python API

```python
from bt_dynamic import Config, load_jsonl, run_day, summarize

config = Config.load("your-config.json")
df = load_jsonl("your-bars.jsonl")
trades = run_day(df, "2025-01-07", config)
summarize(trades)
```

## 9セルの枠組み

3 指標を 3 段階（0/1/2）に分類し、2 軸の組み合わせで 9 セルを構成する。3 軸目（方向指標）が BUY / SELL / None を返し、各セルに割り当てたモードがエントリーを決める。

| | 低ボラ (0) | 通常 (1) | 高ボラ (2) |
|---|---|---|---|
| **弱トレンド (0)** | follow / flip / None | 〃 | 〃 |
| **中トレンド (1)** | 〃 | 〃 | 〃 |
| **強トレンド (2)** | 〃 | 〃 | 〃 |

どのセルに何を割り当てるかが「答え」であり、それは設定 JSON で注入する。`examples/trend/config.json` にあるのは説明用の教科書的ダミー（強トレンド → follow、弱トレンド → flip）で、推奨でも実運用値でもない。

## 開発

```bash
pip install -e . --group dev
pytest
```

`examples/trend/` の合成データは `python examples/trend/generate_data.py` で再生成できる（シード付き乱数ウォークであり実データではない）。

## License

MIT
