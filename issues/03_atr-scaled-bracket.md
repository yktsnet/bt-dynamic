## feat: TP/SL を ATR 倍数で指定できるようにする
id: 03
branch-slug: atr-scaled-bracket
github_issue:
status: draft
type: feat
対象: src/bt_dynamic/config.py, src/bt_dynamic/engine.py, tests/test_config.py, tests/test_engine.py, docs/guarantees.md, CHANGELOG.md
内容: ブラケットの幅を固定 pips だけでなく、エントリー時点の ATR の倍数でも指定できるようにする。既定は現行どおり固定 pips。
確認: `nix-shell -p "python3.withPackages(ps: with ps; [pandas numpy pytest])" --run "PYTHONPATH=src pytest tests -q"` が通ること。`resolve_entry` の既存シグネチャでの呼び出しが壊れていないこと（下の「後方互換」参照）。

---

### 保証

- 新たに宣言する保証
  - `Params` に ATR 倍数の指定手段が増え、指定した場合の TP/SL は「エントリー判定を行うバー時点までの ATR」× 倍率で決まる。判定バーより後のデータは使わない
  - 倍率を指定しない既定の設定では、トレード列が現行と**完全に一致**する（既存の固定 pips 経路に一切影響しない）
  - 固定 pips と ATR 倍数の両方を同時に指定した場合の優先順位が決まっており、曖昧なまま黙って動くことがない
- 維持する保証（`docs/guarantees.md` §7 より）
  - `resolve_entry(price, mode, bias, params)` は `follow` でバイアス方向、`flip` で逆方向のポジションを組み、`mode` または `bias` が `None` なら `None` を返す
  - `run_day` の各トレードは `exit ∈ {TP, SL, EOD}`・`direction ∈ {BUY, SELL}`・`exit_time > entry_time` を満たす
  - `regime_strategy` に無いセルは flat
  - `summarize_dict` は `json.dumps` 可能な素の型だけを返す
- 台帳の変更: §7 の「TP 決済の `result_pips` は `tp_pips - commission_pips` に一致する」は固定 pips モードに限る条件になる。ATR モードでの表現に書き直すため `docs/guarantees.md` を対象に含める

---

### なぜ

`tree/000`（priv 側の実験台帳）で、この戦略の損益の大半が方向の予測ではなく
**ブラケット形状によるボラティリティ・エクスポージャー**で説明されることが分かった。
TP が SL の5倍遠い非対称ブラケットは、値動きがどちらに大きくても平均が正になる
ペイオフを持ち、その寄与は年別で +0.46 〜 -0.66 pips/trade と大きく振れる。

またセル別成績では、ボラティリティ高の列が3つのトレンド強度すべてで負だった。
これが「高ボラという局面が悪い」のか「固定 10pips のストップが高ボラで機械的に
狩られている」のかは、幅をボラに追随させてみないと分離できない。

後者なら、ATR 倍数化でボラ軸の効果自体が消え、分類の次元をひとつ落とせる。

### 要件

1. **ATR は既存のものを使い回す。** エンジンは `IndicatorSet.compute_ax2` で既に
   ATR 系列を計算している（`engine.run_day`）。二本目の ATR 計算を足さない。
   指標を差し替えている利用者にとっても、ブラケットの基準は「その利用者の ax2」に
   なるのが一貫している
2. **先読みしない。** 幅を決めるのは、エントリー判定を行うバーまでの情報だけ。
   建玉後に幅が動かないこと（同一ポジションの TP/SL は建てた時点で固定）
3. **単位。** ax2 は価格単位、`tp_pips`/`sl_pips` は pips 単位。変換は `params.pip` を通す
4. **既定の非破壊。** 倍率を指定しなければ現行と完全に同一の結果になること。
   既存テストが1件も落ちない形で入れる
5. **優先順位の明示。** 固定 pips と倍率の両方が指定されたときの扱いを決め、
   `Config` の検証で弾くか、どちらかを優先すると明記するかのいずれかにする。
   黙ってどちらかが勝つ形にしない

### 後方互換（重要）

`resolve_entry(price, mode, bias, params)` は**パッケージ外から直接呼ばれている**。
本番実行層（priv-live-dynamic の `strategies/trend/strategy.py`）がこのシグネチャで
呼んでおり、ここが壊れると実弾側が止まる。

幅の計算にはバーごとの ATR 値が要るため、`resolve_entry` に新しい入力が必要になる。
**既存の4引数呼び出しがそのまま動き続ける形**（新引数はキーワード引数で既定値あり、
未指定なら固定 pips 経路）にすること。

### テスト

- 倍率未指定で、既存の合成データに対するトレード列が現行と一致すること
- 倍率指定時、TP/SL の幅が判定バー時点の ax2 × 倍率 × (1/pip) に一致すること
- ボラティリティが途中で変わる合成データで、幅がバーごとに変わること（固定 pips では
  変わらないこと）と、建玉後は動かないこと
- 両方指定したときの扱い（弾くなら `ValueError`、優先するならその順序）

### やらないこと

- 既定値の変更。既定は固定 pips のまま
- 倍率の推奨値の提示。どの倍率を使うかは利用者側（priv-bt-dynamic の実験台帳）の責務
