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

```bash
bt-dynamic --config examples/trend/config.json --data examples/trend/data/sample_m5.jsonl
```

- `--config`: パラメータとセル対応表（`regime_strategy`）を持つ JSON。`$BT_DYNAMIC_CONFIG` でも指定可
- `--data`: JSONL のバーデータ（`time_utc` / `open` / `high` / `low` / `close`）。リポにデータは同梱しない。利用者が Dukascopy 等から自取得する
- `--dynamic`: 閾値を固定値でなく直近営業日のパーセンタイルから動的に導出する

Python API:

```python
from bt_dynamic import Config, load_jsonl, run_day, summarize

config = Config.load("your-config.json")
df = load_jsonl("your-bars.jsonl")
trades = run_day(df, "2025-01-07", config)
summarize(trades)
```

指標は差し替え可能（デフォルトは ADX / ATR / RSI）:

```python
from bt_dynamic import IndicatorSet, run_day

my_indicators = IndicatorSet(
    compute_ax1=my_trend_strength,   # 軸1: トレンド強度
    compute_ax2=my_volatility,       # 軸2: ボラティリティ
    compute_direction=my_oscillator, # 方向バイアス（中心値付き振動子）
)
trades = run_day(df, "2025-01-07", config, indicators=my_indicators)
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
