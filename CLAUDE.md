# bt-dynamic

@context/conventions.md
@context/structure.md

## Identity (One-sentence Definition)

汎用部分 = 9セル動的レジーム切替のバックテストエンジン（pip package `bt-dynamic` / import `bt_dynamic`）。
固有部分 = 本番の対応表・実パラメータ・成績・通貨ペア（すべて設定 JSON の外部注入でリポ外、本番実行層側）。

型はハイブリッド: コアは**組み込み型**（本番実行層が pip で組み込むため PyPI 配布）、リポ全体は**研究型**（問いと手法を見せる clone リファレンス）。

## Invariants

- `src/bt_dynamic/` にドメインのエッジを置かない。対応表・閾値は Config 経由の注入のみ。
- `examples/` には中立・教科書的ダミー値と合成データのみ。本番値・実データ・成績を置かない（dotfiles 側 `config.json` の値は本番値であり持ち込まない）。
- コアは戦略側を import しない（一方向依存）。
- 詳細な線引きは README.md「Scope」に従う。

## Commands

```bash
# 開発インストール
pip install -e .

# 合成サンプルでバックテスト実行
bt-dynamic --config examples/trend/config.json --data examples/trend/data/sample_m5.jsonl

# デモ GIF 再生成
nix-shell -p vhs jq "python3.withPackages(ps: with ps; [pandas numpy])" --run 'vhs examples/trend/demo.tape'
```

## Verification

```bash
PYTHONPATH=src pytest -q
```

pandas/numpy が環境にない場合:

```bash
nix-shell -p "python3.withPackages(ps: with ps; [pandas numpy pytest])" --run "PYTHONPATH=src pytest -q"
```

CI（`.github/workflows/ci.yml`）は `pip install -e . pytest` の上で同じ `pytest -q` を走らせる。
