# 実データの取得

標準の使い方は「利用者が自分で実データを取得して回す」。リポにデータは同梱せず（合成サンプルはデモ・テスト用）、取得したデータを再配布もしない。自分で取得して使う分には各ソースの規約上問題ない。

## Dukascopy（主・API key 不要）

[dukascopy-node](https://github.com/Leo4815162342/dukascopy-node) で取得する。1h足なら十分に軽い。

```bash
# 例: EURUSD の 1h 足を 3 ヶ月分
npx dukascopy-node -i eurusd -from 2025-01-01 -to 2025-03-31 -t h1 -f json

# エンジンの JSONL 形式へ変換
bt-dynamic-convert download/eurusd-h1-*.json -o bars.jsonl

# バックテスト
bt-dynamic --config my-config.json --data bars.jsonl
```

`-f csv` の出力もそのまま `bt-dynamic-convert` に渡せる。

## 1h 足で使うときのパラメータ

時間ではなく**バー本数**基準のパラメータは、足の粒度に合わせて読み替える。

| パラメータ | 5分足での意味 | 1h足での例 |
|---|---|---|
| `bars_per_window: 6` | 30分ごとに判定 | `2`（2時間ごとに判定）|
| `ax2_mean_bars: 48` | 4時間平均 | `24`（約1日平均）|
| `trade_end_hour: 17` | UTC 17時クローズ | そのまま（時刻基準）|

`pip` は通貨ペアに合わせる（JPY クロスは `0.01`、それ以外は `0.0001`）。

ウォームアップに前営業日のバーを使うため、バックテスト対象期間の**前営業日を含めて**取得すること（`--dynamic` を使う場合は lookback 営業日分さらに前から）。

## Alpha Vantage（従）

公式無料 API（`FX_INTRADAY` 等）。利用者が自分の API key を投入する。60min interval が 1h 足に相当する。JSON をバーごとの `time_utc / open / high / low / close` に変換すれば同様に使える。

## yfinance

規約がグレーなため動作確認用オプションに留める。

## 規約上の注意

- 取得したデータの塊を再配布しない（リポ・記事・デモへの同梱を含む）
- 画面に数行映す程度の提示（de minimis）は可
- 取引プラットフォーム（Saxo 等）由来のデータは各社の利用規約に従い、公開物に含めない
