# examples/trend — トレンドフォロー適用例

9 セル枠組みをトレンド強度（ADX）× ボラティリティ比（ATR / その移動平均）× 方向バイアス（RSI）に当てはめた適用例。

## 実行

```bash
pip install bt-dynamic
bt-dynamic --config config.json --data data/sample_m5.jsonl
```

動的閾値（直近 3 営業日のパーセンタイルから ax1 / vol の閾値を導出）:

```bash
bt-dynamic --config config.json --data data/sample_m5.jsonl --dynamic
```

## 中身

- `config.json` — **説明用の教科書的ダミー設定**。対応表は「強トレンドで follow、弱トレンドで flip」という素朴な割り当てで、推奨でも実運用値でもない。自分の対応表・閾値はこのファイルを差し替えて注入する
- `data/sample_m5.jsonl` — **合成データ**（シード付き乱数ウォーク、5 営業日分の 5 分足）。実在の相場ではない。`python generate_data.py` で再生成できる
- 実データで走らせる場合は Dukascopy（key 不要）等から自取得し、同じ JSONL 形式（`time_utc` / `open` / `high` / `low` / `close`）に変換する。データの再配布は各ソースの規約に従うこと

## 出力の読み方

デモ出力の成績は合成データ × ダミー設定の結果であり、いかなる実運用とも無関係。数字ではなく「セルごとにモードが切り替わる仕組み」と「exit / cell / regime 別に分解して検証する作法」を見るためのもの。
